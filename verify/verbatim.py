"""Check that a pasted quote appears verbatim in the scraped article text.

Debate evidence must be quoted exactly, so this is a guardrail: if the quote
isn't found, the UI warns the student. We normalize whitespace and curly vs.
straight quotation marks/apostrophes so trivial formatting differences between
the student's paste and the scraped body don't trigger false alarms — but the
words must match.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Curly quotes/apostrophes and dashes -> their plain ASCII equivalents.
_TRANSLATIONS = {
    ord("‘"): "'",  # left single quote
    ord("’"): "'",  # right single quote / apostrophe
    ord("“"): '"',  # left double quote
    ord("”"): '"',  # right double quote
    ord("–"): "-",  # en dash
    ord("—"): "-",  # em dash
}


def _normalize(text: str) -> str:
    """Collapse whitespace and fold curly punctuation to ASCII."""
    folded = text.translate(_TRANSLATIONS)
    return re.sub(r"\s+", " ", folded).strip()


@dataclass
class VerbatimResult:
    """Whether the quote was located in the article."""

    found: bool


def find_quote(quote: str, article_text: str) -> VerbatimResult:
    """True when `quote` appears in `article_text` after normalization.

    An empty quote or empty article cannot be verified, so both return
    not-found (the UI treats that as "couldn't confirm — check manually").
    """
    nquote = _normalize(quote)
    narticle = _normalize(article_text)
    if not nquote or not narticle:
        return VerbatimResult(found=False)
    return VerbatimResult(found=nquote in narticle)
