"""Core citation engine: turns gathered fields into a Stoa-format evidence card.

This package is pure logic with no network access, so it can be unit-tested
offline against the Stoa rules and the Nile brief examples.
"""

from .models import Citation
from .formatter import format_citation, format_citation_html, format_lead

__all__ = ["Citation", "format_citation", "format_citation_html", "format_lead"]
