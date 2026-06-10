"""FastAPI application wiring the scraper + formatter behind a small API.

Endpoints:
  POST /api/scrape       {url, quote} -> {fields, warnings}
  POST /api/format       CitationFields -> {plain, html}
  POST /api/credentials  {authors, publication, url} -> {short_credential, qualifications}
  GET  /                 the single-page frontend
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from citation_engine import format_citation, format_citation_html
from scraper.fetch import fetch_html, FetchError
from scraper.extract import extract_from_html
from .schemas import CitationFields, ScrapeRequest, CredentialsRequest
from .converters import citation_from_fields, build_scrape_response
from .ratelimit import limiter, credentials_limit, scrape_limit

app = FastAPI(title="Citation Machine")

# Register the limiter and a JSON 429 handler consistent with the other
# endpoints' {"error": ...} shape, so the frontend handles it uniformly.
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def _rate_limited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": "Too many requests — wait a bit and try again."},
    )


_STATIC = Path(__file__).parent / "static"


@app.post("/api/scrape")
@limiter.limit(scrape_limit)
def api_scrape(request: Request, req: ScrapeRequest):
    """Fetch + extract a page into editable fields, with warnings."""
    try:
        fetched = fetch_html(req.url)
    except FetchError as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
    result = extract_from_html(fetched.html, fetched.final_url)
    return build_scrape_response(result, req.quote)


@app.post("/api/format")
def api_format(fields: CitationFields):
    """Render the (possibly edited) fields to plain text + HTML."""
    citation = citation_from_fields(fields)
    return {"plain": format_citation(citation), "html": format_citation_html(citation)}


@app.post("/api/credentials")
@limiter.limit(credentials_limit)
def api_credentials(request: Request, req: CredentialsRequest):
    """Draft author credentials via Claude web search (Phase 4).

    Rate-limited (it makes billable Claude + web-search calls) and degrades to a
    503 when drafting is unavailable, so the UI falls back to manual entry.
    """
    try:
        from credentials.drafter import draft_credentials, CredentialError
    except ImportError:
        return JSONResponse(
            status_code=503,
            content={"error": "Credential drafting not available yet."},
        )
    try:
        return draft_credentials(authors=req.authors, publication=req.publication, url=req.url)
    except CredentialError as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (_STATIC / "index.html").read_text(encoding="utf-8")


app.mount("/static", StaticFiles(directory=_STATIC), name="static")
