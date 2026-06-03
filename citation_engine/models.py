"""Data model for a single piece of debate evidence.

The field set is driven directly by the Stoa requirements:
  - Team Policy Debate Rules 2022-23, sec. H.2.b (required citation parts)
  - Evidence Philosophy and Standards 2024-25, sec. I.3 (complete source citation)

Anything the engine cannot determine is left as None so the web layer can show
an editable blank rather than inventing a value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


# Placeholder strings the Stoa standards explicitly ask for when a field is
# genuinely unavailable (Evidence Standards sec. I.3).
NO_AUTHOR = "No author provided"
NO_DATE = "No publication date available"


@dataclass
class Citation:
    """All the pieces needed to render one evidence card.

    Required-by-rule fields come first; qualifications is "strongly encouraged"
    by the Evidence Standards and is the value-add of this tool.
    """

    # Where the student got it. Always supplied by the student for web sources.
    url: str | None = None

    # The verbatim passage the student is quoting. Required, read first word of a
    # sentence to ending punctuation (Rules H.2.c).
    quote: str = ""

    # All authors. Empty list -> rendered as NO_AUTHOR.
    authors: list[str] = field(default_factory=list)

    # Author credentials / bio. Drafted by the qualification finder in a later
    # phase; reviewed by the student before use.
    qualifications: str | None = None

    # Headline of the article / chapter.
    title: str | None = None

    # Name of the publication or website (e.g. "CSIS", "New York Times").
    publication: str | None = None

    # Publication date. None -> rendered as NO_DATE (and access_date carries
    # the verification weight, per Rules H.2.b.iii).
    pub_date: date | None = None

    # When the student retrieved the page. Required for electronic sources.
    access_date: date | None = None

    # Only for printed sources (books / large documents), per Rules H.2.b.v.
    page_number: str | None = None

    def author_string(self) -> str:
        """Render the author list the way debate cards do.

        One author: "Jane Doe". Two: "Jane Doe and John Roe".
        Three or more: "Jane Doe, John Roe, and Amy Poe".
        No authors: the Stoa placeholder.
        """
        names = [a.strip() for a in self.authors if a and a.strip()]
        if not names:
            return NO_AUTHOR
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return ", ".join(names[:-1]) + f", and {names[-1]}"
