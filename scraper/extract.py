"""Turn fetched HTML into a partially filled Citation + article text.

Metadata extraction uses trafilatura, which reads OpenGraph / JSON-LD / meta
tags and the article body. We deliberately keep the mapping (build_result) as a
pure function so it can be unit-tested offline without network or trafilatura.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import trafilatura

from citation_engine import Citation


@dataclass
class ScrapeResult:
    """Everything the scraper learned about a page."""

    citation: Citation
    article_text: str = ""  # full main text, for verbatim/contiguity checks
    warnings: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)  # raw metadata, for the UI / debugging


_CITATION_AUTHOR_RE = re.compile(
    r"""<meta\b[^>]*?\bname=["']citation_author["'][^>]*?\bcontent=["']([^"']+)["']""",
    re.IGNORECASE,
)


def parse_citation_authors(html: str) -> list[str]:
    """Pull Google Scholar / Highwire `citation_author` tags from raw HTML.

    Journals and many news sites emit one tag per author in clean 'Last, First'
    form. trafilatura ignores these, so we read them directly. Order preserved.
    """
    if not html:
        return []
    return [m.strip() for m in _CITATION_AUTHOR_RE.findall(html) if m.strip()]


def normalize_author_name(raw: str) -> str:
    """Render a single author name as 'First Last'.

    Citation metadata (Google Scholar / Highwire `citation_author` tags) gives
    one name per tag in 'Last, First' order. A single comma means we swap; a
    plain 'First Last' (no comma) is returned untouched. We never touch names
    with two or more commas, which are ambiguous and left for human review.
    """
    name = raw.strip()
    parts = [p.strip() for p in name.split(",")]
    if len(parts) == 2 and all(parts):
        last, first = parts
        return f"{first} {last}"
    return name


def looks_like_username(name: str) -> bool:
    """True if a name looks like a handle rather than a real person's byline.

    Real bylines have a space between given and family name. A single
    whitespace-free token — 'adamgriffiths', 'Adamgriffiths', 'jsmith2',
    'Staff' — is almost always a CMS username, handle, or org placeholder, so
    we keep the value (never invent) but warn the student to verify it.
    """
    token = name.strip()
    return bool(token) and " " not in token


_TITLE_SEPARATORS = ("|", "—", "–", "-", ":")


def clean_title(title: str | None, publication: str | None) -> str | None:
    """Strip a trailing ' <sep> <publication>' tail from a page title.

    Many sites append their own name to the <title> ('Story - FP Analytics').
    We only remove the tail when its text matches the known publication, so a
    legitimate dash inside a real headline is never touched.
    """
    if not title:
        return title
    t = title.strip()
    if not publication:
        return t
    pub = publication.strip().lower()
    for sep in _TITLE_SEPARATORS:
        marker = f" {sep} "
        idx = t.rfind(marker)
        if idx != -1 and t[idx + len(marker):].strip().lower() == pub:
            return t[:idx].strip()
    return t


def _split_authors(author: str | None) -> list[str]:
    """trafilatura returns authors as one string, usually '; '-separated."""
    if not author:
        return []
    raw = author.replace(" and ", ";").split(";")
    seen: list[str] = []
    for name in (a.strip() for a in raw):
        if name and name not in seen:
            seen.append(name)
    return seen


def _parse_date(value: str | None) -> date | None:
    """trafilatura dates are ISO 'YYYY-MM-DD'; be tolerant of partials."""
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def build_result(meta: dict, url: str) -> ScrapeResult:
    """Pure mapping from a metadata dict to a ScrapeResult.

    `meta` keys: title, author, date, sitename, hostname, text.
    """
    publication = (meta.get("sitename") or meta.get("hostname") or "").strip() or None

    # Prefer structured citation_author tags (one clean name each) over
    # trafilatura's single mangled author string.
    citation_authors = meta.get("citation_authors") or []
    if citation_authors:
        authors = [normalize_author_name(a) for a in citation_authors if a and a.strip()]
    else:
        authors = [normalize_author_name(a) for a in _split_authors(meta.get("author"))]

    pub_date = _parse_date(meta.get("date"))
    title = clean_title((meta.get("title") or "").strip() or None, publication)
    article_text = meta.get("text") or ""

    citation = Citation(
        url=url,
        authors=authors,
        title=title,
        publication=publication,
        pub_date=pub_date,
        access_date=date.today(),
    )

    warnings: list[str] = []
    if not authors:
        warnings.append("No author found - confirm or enter manually.")
    else:
        flagged = [a for a in authors if looks_like_username(a)]
        for a in flagged:
            warnings.append(
                f"Author '{a}' looks like a username, not a real name - verify."
            )
    if pub_date is None:
        warnings.append("No publication date found - using access date only.")
    if not title:
        warnings.append("No article title found.")
    if not article_text:
        warnings.append("No article body extracted - verbatim check unavailable.")

    raw = {k: meta.get(k) for k in ("title", "author", "date", "sitename", "hostname")}
    return ScrapeResult(
        citation=citation, article_text=article_text, warnings=warnings, raw=raw
    )


def extract_from_html(html: str, url: str) -> ScrapeResult:
    """Run trafilatura over HTML and build a ScrapeResult."""
    doc = trafilatura.bare_extraction(html, with_metadata=True, url=url)
    if doc is None:
        empty = build_result({}, url)
        empty.warnings.insert(0, "Could not extract content from this page.")
        return empty

    meta = {
        "title": getattr(doc, "title", None),
        "author": getattr(doc, "author", None),
        "citation_authors": parse_citation_authors(html),
        "date": getattr(doc, "date", None),
        "sitename": getattr(doc, "sitename", None),
        "hostname": getattr(doc, "hostname", None),
        "text": getattr(doc, "text", None),
    }
    return build_result(meta, url)
