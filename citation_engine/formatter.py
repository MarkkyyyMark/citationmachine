"""Render a Citation into the Stoa evidence-card format.

The exact-wording contract lives in docs/citation-format-spec.md. In short, a
card is one block:

    <LEAD>. [(<qualifications>) ]"<title>" <publisher>, <full date>. Accessed <today> <url>
        <verbatim quote, double-indented>

Only the LEAD is bold. The lead carries month+year; the full publication date
appears in the body. `format_citation` renders plain text; `format_citation_html`
renders the same content with the lead bolded so it survives copy-paste into a
Google Doc.
"""

from __future__ import annotations

from datetime import date
from html import escape

from .models import Citation, NO_AUTHOR, NO_DATE


def _fmt_full_date(d: date | None) -> str:
    """'January 5, 2026' with no leading zero on the day."""
    if d is None:
        return NO_DATE
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def _fmt_month_year(d: date | None) -> str:
    """'January 2026' for the short lead."""
    if d is None:
        return NO_DATE
    return f"{d.strftime('%B')} {d.year}"


def format_lead(c: Citation) -> str:
    """The bold lead: '<identifier>, [<middle>, ]<Month Year>.'

    identifier = author(s) if present, else publisher, else the Stoa
    placeholder. middle = 'No author provided' when there is no author,
    otherwise the short credential if we have one.
    """
    if c.authors:
        identifier = c.author_string()
        middle = c.short_credential.strip() if c.short_credential and c.short_credential.strip() else None
    else:
        identifier = (c.publication or "").strip() or NO_AUTHOR
        middle = NO_AUTHOR

    parts = [identifier]
    if middle:
        parts.append(middle)
    parts.append(_fmt_month_year(c.pub_date))
    return ", ".join(parts) + "."


def _body_segments(c: Citation) -> list[str]:
    """Everything after the lead, as ordered plain-text segments."""
    segs: list[str] = []

    if c.qualifications and c.qualifications.strip():
        segs.append(f"({c.qualifications.strip()})")

    if c.title and c.title.strip():
        segs.append(f'"{c.title.strip()}"')

    # Publisher + full publication date.
    pub = (c.publication or "").strip()
    date_str = _fmt_full_date(c.pub_date)
    segs.append(f"{pub}, {date_str}." if pub else f"{date_str}.")

    # Printed source -> page number; electronic -> accessed date + URL.
    if c.page_number and c.page_number.strip():
        segs.append(f"p. {c.page_number.strip()}")
    else:
        if c.access_date is not None:
            segs.append(f"Accessed {_fmt_full_date(c.access_date)}")
        if c.url and c.url.strip():
            segs.append(c.url.strip())

    return segs


def format_source_line(c: Citation) -> str:
    """The full single-line citation (lead + body), plain text, no markup."""
    return " ".join([format_lead(c), *_body_segments(c)])


def format_citation(c: Citation, indent: str = "    ") -> str:
    """Full evidence card: source line, then the verbatim quote, indented."""
    line = format_source_line(c)
    if not c.quote.strip():
        return line
    quoted = "\n".join(indent + ln for ln in c.quote.strip().splitlines())
    return f"{line}\n{quoted}"


def format_citation_html(c: Citation) -> str:
    """The card as HTML: lead bolded, URL linked, quote in an indented block.

    Copying the rendered output into Google Docs preserves the bold lead.
    """
    lead = f"<strong>{escape(format_lead(c))}</strong>"

    body_parts: list[str] = []
    for seg in _body_segments(c):
        if c.url and seg == c.url.strip():
            url = escape(seg, quote=True)
            body_parts.append(f'<a href="{url}">{escape(seg)}</a>')
        else:
            body_parts.append(escape(seg))

    line = " ".join([lead, *body_parts])
    quote_html = escape(c.quote.strip())
    if not quote_html:
        return f"<p>{line}</p>"
    return (
        f"<p>{line}</p>\n"
        f'<blockquote style="margin-left:2em">{quote_html}</blockquote>'
    )
