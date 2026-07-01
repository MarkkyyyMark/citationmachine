"""Tests for the web app: pure converters + the /api endpoints.

Network-touching scrape logic is exercised through the pure
`build_scrape_response`; the live fetch is integration-tested separately.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from webapp.main import app
from webapp.schemas import CitationFields
from webapp.converters import citation_from_fields, build_scrape_response
from webapp.ratelimit import limiter
from scraper.extract import ScrapeResult
from citation_engine import Citation

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_limiter():
    # Rate-limit counters live in-process; clear them so counts don't bleed
    # across tests (e.g. a credentials test exhausting the next test's budget).
    limiter.reset()
    yield


def _baskaran_fields() -> dict:
    return {
        "url": "https://www.csis.org/analysis/new-executive-order",
        "quote": "critical minerals have emerged as a prominent element",
        "authors": ["Gracelin Baskaran"],
        "short_credential": "Director of the Critical Minerals Security Program at CSIS",
        "qualifications": "Dr. Gracelin Baskaran is director of the program at CSIS",
        "title": "New Executive Order Ties U.S. Critical Minerals Security to Global Partnerships",
        "publication": "CSIS",
        "pub_date": "2026-01-15",
        "access_date": "2026-01-20",
        "page_number": None,
    }


# --- pure converter ---

def test_citation_from_fields_parses_iso_dates():
    c = citation_from_fields(CitationFields(**_baskaran_fields()))
    assert isinstance(c, Citation)
    assert c.pub_date == date(2026, 1, 15)
    assert c.access_date == date(2026, 1, 20)
    assert c.authors == ["Gracelin Baskaran"]


def test_citation_from_fields_handles_missing_dates():
    fields = _baskaran_fields() | {"pub_date": None, "access_date": None}
    c = citation_from_fields(CitationFields(**fields))
    assert c.pub_date is None
    assert c.access_date is None


# --- scrape response building (pure) ---

def _result(article_text: str) -> ScrapeResult:
    return ScrapeResult(
        citation=Citation(authors=["Gracelin Baskaran"], title="T", publication="CSIS"),
        article_text=article_text,
        warnings=[],
    )


def test_scrape_response_warns_when_quote_absent():
    resp = build_scrape_response(_result("Totally different body text."), "a missing quote")
    assert any("not found" in w.lower() for w in resp["warnings"])


def test_scrape_response_no_quote_warning_when_present():
    body = "Here critical minerals have emerged as a prominent element of policy."
    resp = build_scrape_response(_result(body), "critical minerals have emerged as a prominent element")
    assert not any("not found" in w.lower() for w in resp["warnings"])


# --- /api/format endpoint ---

def test_format_endpoint_returns_plain_and_html():
    r = client.post("/api/format", json=_baskaran_fields())
    assert r.status_code == 200
    data = r.json()
    assert data["plain"].startswith(
        "Gracelin Baskaran, Director of the Critical Minerals Security Program at CSIS, January 2026."
    )
    assert "<strong>Gracelin Baskaran" in data["html"]


def test_format_endpoint_no_author_uses_publisher():
    fields = _baskaran_fields() | {"authors": [], "short_credential": None,
                                   "qualifications": None}
    r = client.post("/api/format", json=fields)
    assert r.status_code == 200
    assert r.json()["plain"].startswith("CSIS, No author provided, January 2026.")


# --- index page served ---

def test_index_page_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_credentials_without_key_returns_503(monkeypatch):
    # No API key -> the endpoint must degrade to 503, not crash, so the UI
    # falls back to manual credential entry.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post(
        "/api/credentials",
        json={"authors": ["Jane Doe"], "publication": "CSIS", "url": "https://csis.org/x"},
    )
    assert r.status_code == 503
    assert "error" in r.json()


# --- Phase 7 hardening: rate limits + input caps ---

def test_credentials_rate_limited(monkeypatch):
    # The billable endpoint must shed load: past the cap, callers get 429 with a
    # JSON error (the UI falls back to manual). Set a tiny cap to make it cheap.
    monkeypatch.setenv("RATE_CREDENTIALS", "2/minute")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)  # 503 before any real call
    payload = {"authors": ["X"], "publication": "Y", "url": "https://z.com/a"}
    statuses = [client.post("/api/credentials", json=payload).status_code for _ in range(3)]
    assert statuses[:2] == [503, 503]   # within cap -> normal degraded path
    assert statuses[2] == 429           # over cap -> rate limited
    assert "error" in client.post("/api/credentials", json=payload).json()


def test_client_ip_keys_on_proxy_appended_hop():
    # Render's proxy APPENDS the real client IP as the last X-Forwarded-For hop;
    # any earlier hops arrived from the client and can be forged. Keying on the
    # first hop would hand every attacker a fresh rate-limit bucket per request.
    from starlette.requests import Request
    from webapp.ratelimit import client_ip

    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"6.6.6.6, 203.0.113.7")],
        "client": ("127.0.0.1", 1234),
    }
    assert client_ip(Request(scope)) == "203.0.113.7"


def test_credentials_rate_limit_survives_spoofed_forwarded_for(monkeypatch):
    # An attacker rotating a fake X-Forwarded-For prefix must NOT escape the cap
    # on the billable endpoint — all three requests share the real client's bucket.
    monkeypatch.setenv("RATE_CREDENTIALS", "2/minute")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)  # 503 before any real call
    payload = {"authors": ["X"], "publication": "Y", "url": "https://z.com/a"}
    statuses = [
        client.post(
            "/api/credentials",
            json=payload,
            headers={"X-Forwarded-For": f"10.0.0.{i}, 203.0.113.7"},
        ).status_code
        for i in range(3)
    ]
    assert statuses[:2] == [503, 503]   # within cap -> normal degraded path
    assert statuses[2] == 429           # spoofed prefixes don't buy a fresh bucket


def test_scrape_rejects_oversized_url():
    # An over-long URL is rejected at validation (422) before any network fetch.
    r = client.post("/api/scrape", json={"url": "https://x.com/" + "a" * 5000, "quote": ""})
    assert r.status_code == 422


def test_credentials_rejects_too_many_authors(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post(
        "/api/credentials",
        json={"authors": ["a"] * 50, "publication": "CSIS", "url": "https://csis.org/x"},
    )
    assert r.status_code == 422


def test_credentials_accepts_real_multi_author_count(monkeypatch):
    # Regression: the CSIS "Russia-Ukraine War in 10 Charts" page has 11 authors.
    # A cap of 10 rejected it at validation (422) before the drafter ran, so the
    # UI reported "unavailable". A real 11-author piece must NOT be a 422 — with
    # no API key it should reach the drafter and degrade to 503 instead.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post(
        "/api/credentials",
        json={"authors": [f"Author {i}" for i in range(11)],
              "publication": "CSIS", "url": "https://csis.org/x"},
    )
    assert r.status_code != 422
    assert r.status_code == 503  # no key -> drafter's degraded path, not a validation reject
