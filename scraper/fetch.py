"""Fetch raw HTML from a URL.

Uses a real browser User-Agent because many publishers (CSIS, news sites)
return nothing to the default library agent. TLS verification is ON by default;
it can be disabled only via the CITATION_SCRAPER_VERIFY_SSL=0 env var, which is
intended solely for local machines behind a TLS-intercepting proxy. Never set
that in production.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

# Defer TLS verification to the operating system's certificate store. Without
# this, Python's bundled `certifi` list rejects the certificates injected by
# school / corporate / antivirus TLS-intercepting proxies, and every fetch
# fails with "unable to get local issuer certificate" even though the browser
# trusts the page. truststore fixes that transparently for requests.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:  # pragma: no cover - truststore is a hard runtime dep
    pass

# A current desktop Chrome UA. Some sites gate content on a plausible browser.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class FetchError(Exception):
    """Raised when a page cannot be retrieved as usable HTML."""


@dataclass
class FetchResult:
    html: str
    final_url: str  # after redirects
    status_code: int


def _verify_ssl() -> bool:
    return os.environ.get("CITATION_SCRAPER_VERIFY_SSL", "1") != "0"


def fetch_html(url: str, *, timeout: int = 25) -> FetchResult:
    """GET `url` and return its HTML, following redirects.

    Raises FetchError on network problems, non-HTML responses, or HTTP errors.
    """
    if not url or not url.lower().startswith(("http://", "https://")):
        raise FetchError(f"Not a valid http(s) URL: {url!r}")

    verify = _verify_ssl()
    if not verify:
        # Quiet the urllib3 warning when verification is intentionally off (dev).
        import urllib3

        urllib3.disable_warnings()

    try:
        resp = requests.get(
            url, headers=_HEADERS, timeout=timeout, verify=verify, allow_redirects=True
        )
    except requests.RequestException as exc:
        raise FetchError(f"Could not fetch {url}: {exc}") from exc

    if resp.status_code >= 400:
        raise FetchError(f"{url} returned HTTP {resp.status_code}")

    ctype = resp.headers.get("Content-Type", "")
    if ctype and "html" not in ctype.lower() and "xml" not in ctype.lower():
        raise FetchError(f"{url} is not an HTML page (Content-Type: {ctype})")

    return FetchResult(html=resp.text, final_url=str(resp.url), status_code=resp.status_code)
