"""Phase 2: fetch a web page and extract citation metadata + article text.

Public entry point is `scrape(url)`, which returns a ScrapeResult containing a
partially filled Citation, the full article text (used by the Phase 3 verbatim
verifier), and warnings for any fields that could not be found.
"""

from .fetch import fetch_html, FetchError
from .extract import extract_from_html, build_result, ScrapeResult


def scrape(url: str, *, timeout: int = 25) -> ScrapeResult:
    """Fetch `url` and extract everything we can for a citation."""
    fetched = fetch_html(url, timeout=timeout)
    return extract_from_html(fetched.html, fetched.final_url)


__all__ = [
    "scrape",
    "fetch_html",
    "FetchError",
    "extract_from_html",
    "build_result",
    "ScrapeResult",
]
