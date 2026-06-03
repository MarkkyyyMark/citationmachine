"""Tests for the citation engine, anchored to the real Stoa/Nile examples."""

from datetime import date

from citation_engine import Citation, format_citation
from citation_engine.formatter import format_source_line
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
        qualifications=quals,
        title="New Executive Order Ties U.S. Critical Minerals Security to Global Partnerships",
        pub_date=date(2026, 1, 15),
        access_date=date(2026, 1, 20),
    )


def test_source_line_matches_nile_order():
    line = format_source_line(_baskaran())
    expected = (
        'Gracelin Baskaran, January 15, 2026, '
        '(Dr. Gracelin Baskaran is director of the Critical Minerals Security '
        'Program at the Center for Strategic and International Studies (CSIS)) '
        '"New Executive Order Ties U.S. Critical Minerals Security to Global Partnerships" '
        'Accessed January 20, 2026 '
        'https://www.csis.org/analysis/new-executive-order-ties-us-critical-minerals-security-global-partnerships'
    )
    assert line == expected


def test_full_card_indents_quote():
    card = format_citation(_baskaran())
    lines = card.splitlines()
    assert lines[0].startswith("Gracelin Baskaran,")
    assert lines[1].startswith("    During President Trump")


def test_no_leading_zero_on_day():
    c = Citation(pub_date=date(2026, 1, 5), authors=["A"])
    assert "January 5, 2026" in format_source_line(c)


def test_missing_author_uses_placeholder():
    c = Citation(authors=[], pub_date=date(2026, 1, 1))
    assert format_source_line(c).startswith(f"{NO_AUTHOR},")


def test_missing_date_uses_placeholder():
    c = Citation(authors=["Jane Doe"], pub_date=None, access_date=date(2026, 1, 1))
    line = format_source_line(c)
    assert NO_DATE in line
    # Access date still present so the evidence remains verifiable.
    assert "Accessed January 1, 2026" in line


def test_author_joining():
    assert Citation(authors=["A Bee"]).author_string() == "A Bee"
    assert Citation(authors=["A Bee", "C Dee"]).author_string() == "A Bee and C Dee"
    assert (
        Citation(authors=["A Bee", "C Dee", "E Eff"]).author_string()
        == "A Bee, C Dee, and E Eff"
    )


def test_printed_source_uses_page_not_url():
    c = Citation(
        authors=["Jane Doe"],
        pub_date=date(2020, 6, 1),
        title="Some Book",
        page_number="42",
    )
    line = format_source_line(c)
    assert "p. 42" in line
    assert "Accessed" not in line


def test_qualifications_omitted_when_absent():
    c = Citation(authors=["Jane Doe"], pub_date=date(2020, 1, 1), title="X")
    assert "(" not in format_source_line(c)
