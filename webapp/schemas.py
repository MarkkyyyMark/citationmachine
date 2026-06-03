"""Request/response shapes for the API.

Dates cross the wire as ISO strings ('YYYY-MM-DD') so the browser's native date
inputs can bind to them; the converters turn them into datetime.date.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CitationFields(BaseModel):
    """The full, editable field set — shared by the scrape response and the
    format request. Mirrors citation_engine.Citation, dates as ISO strings."""

    url: str = ""
    quote: str = ""
    authors: list[str] = Field(default_factory=list)
    short_credential: str | None = None
    qualifications: str | None = None
    title: str | None = None
    publication: str | None = None
    pub_date: str | None = None
    access_date: str | None = None
    page_number: str | None = None


class ScrapeRequest(BaseModel):
    url: str
    quote: str = ""


class CredentialsRequest(BaseModel):
    authors: list[str] = Field(default_factory=list)
    publication: str | None = None
    url: str = ""
