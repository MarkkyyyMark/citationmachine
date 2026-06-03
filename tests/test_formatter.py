"""Tests for the citation engine, anchored to the real Stoa/Nile examples.

The exact-wording contract is in docs/citation-format-spec.md.
"""

from datetime import date

from citation_engine import Citation, format_citation
from citation_engine.formatter import format_lead, format_citation_html
from citation_engine.models import NO_AUTHOR, NO_DATE


def _baskaran() -> Citation:
    """The first card from the Nile Critical Minerals brief (page 3)."""
    quals = (
        "Dr. Gracelin Baskaran is director of the Critical Minerals Security "
        "Program at the Center for Strategic and International Studies (CSIS)"
    )
    return Citation(
        url="https://www.csis.org/analysis/new-executive-order-ties-us-critical-minerals-security-global-partnerships",
        quote="During President Trump's second term, critical minerals have emerged as a prominent element of U.S. foreign policy.",
        authors=["Gracelin Baskaran"],
        short_credential="Director of the Critical Minerals Security Program at CSIS",
        qualifications=quals,
        title="New Executive Order Ties U.S. Critical Minerals Security to Global Partnerships",
        publication="CSIS",
        pub_date=date(2026, 1, 15),
        access_date=date(2026, 1, 20),
    )


def _dfc_no_author() -> Citation:
    return Citation(
        url="https://www.dfc.gov/media/press-releases/dfc-secures-expanded-authorities-fy26-ndaa",
        quote="Some verbatim text.",
        authors=[],
        title="DFC Secures Expanded Authorities with FY26 NDAA Signed into Law",
        publication="DFC.gov",
        pub_date=date(2025, 12, 18),
        access_date=date(2026, 6, 2),
    )


# --- the bold lead: identifier, [middle,] Month Year. ---

def test_lead_with_author_and_credential():
    assert format_lead(_baskaran()) == (
        "Gracelin Baskaran, Director of the Critical Minerals Security Program "
        "at CSIS, January 2026."
    )


def test_lead_no_author_uses_publisher_and_placeholder():
    assert format_lead(_dfc_no_author()) == "DFC.gov, No author provided, December 2025."


def test_lead_author_without_credential_omits_middle():
    c = Citation(authors=["Jane Doe"], pub_date=date(2026, 1, 5))
    assert format_lead(c) == "Jane Doe, January 2026."


def test_lead_uses_month_year_only():
    # Day must NOT appear in the lead.
    assert "January 2026" in format_lead(_baskaran())
    assert "January 15" not in format_lead(_baskaran())


# --- full plain-text citation: exact wording ---

def test_full_citation_with_author_exact():
    expected = (
        "Gracelin Baskaran, Director of the Critical Minerals Security Program "
        "at CSIS, January 2026. "
        "(Dr. Gracelin Baskaran is director of the Critical Minerals Security "
        "Program at the Center for Strategic and International Studies (CSIS)) "
        '"New Executive Order Ties U.S. Critical Minerals Security to Global Partnerships" '
        "CSIS, January 15, 2026. "
        "Accessed January 20, 2026 "
        "https://www.csis.org/analysis/new-executive-order-ties-us-critical-minerals-security-global-partnerships"
    )
    card = format_citation(_baskaran())
    assert card.splitlines()[0] == expected


def test_full_citation_no_author_exact():
    expected = (
        "DFC.gov, No author provided, December 2025. "
        '"DFC Secures Expanded Authorities with FY26 NDAA Signed into Law" '
        "DFC.gov, December 18, 2025. "
        "Accessed June 2, 2026 "
        "https://www.dfc.gov/media/press-releases/dfc-secures-expanded-authorities-fy26-ndaa"
    )
    assert format_citation(_dfc_no_author()).splitlines()[0] == expected


def test_full_card_indents_quote():
    card = format_citation(_baskaran())
    lines = card.splitlines()
    assert lines[0].startswith("Gracelin Baskaran,")
    assert lines[1] == (
        "    During President Trump's second term, critical minerals have "
        "emerged as a prominent element of U.S. foreign policy."
    )


def test_qualifications_omitted_when_absent():
    c = Citation(
        authors=["Jane Doe"],
        pub_date=date(2020, 1, 1),
        title="X",
        publication="Site",
        access_date=date(2020, 2, 1),
    )
    # No qualifications -> no parenthetical anywhere in the body.
    body = format_citation(c).splitlines()[0]
    assert "(" not in body


# --- placeholders ---

def test_missing_date_uses_placeholder():
    c = Citation(
        authors=["Jane Doe"], pub_date=None, publication="Site",
        title="X", access_date=date(2026, 1, 1),
    )
    body = format_citation(c).splitlines()[0]
    assert NO_DATE in body
    assert "Accessed January 1, 2026" in body


def test_missing_author_and_publisher_falls_back_to_placeholder():
    c = Citation(authors=[], publication=None, pub_date=date(2026, 1, 1))
    assert format_lead(c).startswith(NO_AUTHOR)


# --- printed source uses page number, not Accessed/URL ---

def test_printed_source_uses_page_not_url():
    c = Citation(
        authors=["Jane Doe"],
        pub_date=date(2020, 6, 1),
        publication="Some Press",
        title="Some Book",
        page_number="42",
    )
    body = format_citation(c).splitlines()[0]
    assert "p. 42" in body
    assert "Accessed" not in body


# --- author joining is unchanged ---

def test_author_joining():
    assert Citation(authors=["A Bee"]).author_string() == "A Bee"
    assert Citation(authors=["A Bee", "C Dee"]).author_string() == "A Bee and C Dee"
    assert (
        Citation(authors=["A Bee", "C Dee", "E Eff"]).author_string()
        == "A Bee, C Dee, and E Eff"
    )


# --- HTML render bolds the lead and keeps the quote ---

def test_html_bolds_only_the_lead():
    html = format_citation_html(_baskaran())
    assert (
        "<strong>Gracelin Baskaran, Director of the Critical Minerals Security "
        "Program at CSIS, January 2026.</strong>"
    ) in html


def test_html_includes_quote_and_link():
    html = format_citation_html(_baskaran())
    assert "During President Trump" in html
    assert 'href="https://www.csis.org/analysis/' in html
