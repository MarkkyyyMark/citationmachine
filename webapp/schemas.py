"""Request/response shapes for the API.

Dates cross the wire as ISO strings ('YYYY-MM-DD') so the browser's native date
inputs can bind to them; the converters turn them into datetime.date.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field

# Caps keep oversized payloads out of the billable LLM call and out of the
# formatter. URLs and quotes are bounded generously; an author name far past
# 200 chars or a list past 10 is abuse, not a real citation.
_URL_MAX = 2000
_QUOTE_MAX = 10_000
_TEXT_MAX = 2000
_AUTHOR_MAX = 200
_AUTHORS_MAX = 10

AuthorStr = Annotated[str, Field(max_length=_AUTHOR_MAX)]


class CitationFields(BaseModel):
    """The full, editable field set — shared by the scrape response and the
    format request. Mirrors citation_engine.Citation, dates as ISO strings."""

    url: str = Field(default="", max_length=_URL_MAX)
    quote: str = Field(default="", max_length=_QUOTE_MAX)
    authors: list[AuthorStr] = Field(default_factory=list, max_length=_AUTHORS_MAX)
    short_credential: str | None = Field(default=None, max_length=_TEXT_MAX)
    qualifications: str | None = Field(default=None, max_length=_TEXT_MAX)
    title: str | None = Field(default=None, max_length=_TEXT_MAX)
    publication: str | None = Field(default=None, max_length=_TEXT_MAX)
    pub_date: str | None = None
    access_date: str | None = None
    page_number: str | None = Field(default=None, max_length=100)


class ScrapeRequest(BaseModel):
    url: str = Field(max_length=_URL_MAX)
    quote: str = Field(default="", max_length=_QUOTE_MAX)


class CredentialsRequest(BaseModel):
    authors: list[AuthorStr] = Field(default_factory=list, max_length=_AUTHORS_MAX)
    publication: str | None = Field(default=None, max_length=_TEXT_MAX)
    url: str = Field(default="", max_length=_URL_MAX)
