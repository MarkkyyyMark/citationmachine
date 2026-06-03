"""Pure conversions between the API field shape and the Citation engine.

Kept network- and framework-free so they can be unit-tested directly.
"""

from __future__ import annotations

from datetime import date

from citation_engine import Citation
from scraper.extract import ScrapeResult
from verify import find_quote
from .schemas import CitationFields


def _parse_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def citation_from_fields(f: CitationFields) -> Citation:
    """Build a Citation from the editable field set."""
    return Citation(
        url=f.url or None,
        quote=f.quote or "",
        authors=list(f.authors),
        short_credential=f.short_credential,
        qualifications=f.qualifications,
        title=f.title,
        publication=f.publication,
        pub_date=_parse_iso(f.pub_date),
        access_date=_parse_iso(f.access_date),
        page_number=f.page_number,
    )


def fields_from_citation(c: Citation, quote: str) -> dict:
    """Serialize a Citation into the API field dict (dates as ISO strings)."""
    return {
        "url": c.url or "",
        "quote": quote,
        "authors": list(c.authors),
        "short_credential": c.short_credential,
        "qualifications": c.qualifications,
        "title": c.title,
        "publication": c.publication,
        "pub_date": c.pub_date.isoformat() if c.pub_date else None,
        "access_date": c.access_date.isoformat() if c.access_date else None,
        "page_number": c.page_number,
    }


def build_scrape_response(result: ScrapeResult, quote: str) -> dict:
    """Turn a ScrapeResult + the student's quote into the scrape API payload.

    Adds a verbatim warning when the quote can't be found in the article body.
    """
    warnings = list(result.warnings)
    if quote.strip() and result.article_text:
        if not find_quote(quote, result.article_text).found:
            warnings.append(
                "Quote not found in the article text - verify it is exact."
            )
    return {"fields": fields_from_citation(result.citation, quote), "warnings": warnings}
