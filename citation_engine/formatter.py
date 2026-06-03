"""Render a Citation into the Stoa evidence-card format.

Target format, taken from the Nile Critical Minerals brief:

    Gracelin Baskaran, January 15, 2026, (Dr. Gracelin Baskaran is director of
    the Critical Minerals Security Program at CSIS...) "New Executive Order Ties
    U.S. Critical Minerals Security to Global Partnerships" Accessed January 20,
    2026 https://www.csis.org/analysis/...
        <verbatim quote, double-indented>

Field order on the source line:
    authors, pub_date, (qualifications) "title" [publication] Accessed <date> <url>
or for a printed source:
    authors, pub_date, (qualifications) "title" [publication] p. <page>
"""

from __future__ import annotations

from datetime import date

from .models import Citation, NO_DATE


def _fmt_date(d: date | None) -> str:
    """Format as 'January 5, 2026' with no leading zero on the day."""
    if d is None:
        return NO_DATE
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def format_source_line(c: Citation) -> str:
    """Build the single-line source citation that sits above the quote."""
    parts: list[str] = []

    # Author, date,
    parts.append(f"{c.author_string()},")
    parts.append(f"{_fmt_date(c.pub_date)},")

    # (Qualifications) -- strongly encouraged; omitted only if we have none.
    if c.qualifications and c.qualifications.strip():
        parts.append(f"({c.qualifications.strip()})")

    # "Title"
    if c.title and c.title.strip():
        parts.append(f'"{c.title.strip()}"')

    # Publication name, when distinct from the title/site already shown.
    if c.publication and c.publication.strip():
        parts.append(c.publication.strip())

    # Retrieval info: printed source -> page number; electronic -> accessed + URL.
    if c.page_number and c.page_number.strip():
        parts.append(f"p. {c.page_number.strip()}")
    else:
        if c.access_date is not None:
            parts.append(f"Accessed {_fmt_date(c.access_date)}")
        if c.url and c.url.strip():
            parts.append(c.url.strip())

    return " ".join(parts)


def format_citation(c: Citation, indent: str = "    ") -> str:
    """Full evidence card: source line, then the verbatim quote, indented.

    The indent visually differentiates evidence from non-evidence, which the
    Evidence Standards (sec. III) require on briefs.
    """
    line = format_source_line(c)
    if not c.quote.strip():
        return line
    quoted = "\n".join(indent + ln for ln in c.quote.strip().splitlines())
    return f"{line}\n{quoted}"
