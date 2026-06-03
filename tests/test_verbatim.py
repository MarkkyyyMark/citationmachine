"""Tests for the verbatim quote checker.

The student's pasted quote must actually appear in the scraped article. We
normalize whitespace and curly/straight quotes so trivial formatting differences
don't raise false alarms, but the words themselves must match.
"""

from verify.verbatim import find_quote


ARTICLE = (
    "During President Trump's second term, critical minerals have emerged\n"
    "as a prominent element of U.S. foreign policy. Analysts say the shift\n"
    "reflects a broader strategy."
)


def test_exact_substring_is_found():
    quote = "critical minerals have emerged as a prominent element of U.S. foreign policy"
    assert find_quote(quote, ARTICLE).found is True


def test_whitespace_and_newline_differences_still_match():
    # Quote uses single spaces; article wraps with a newline mid-phrase.
    quote = "critical minerals have emerged as a prominent element"
    assert find_quote(quote, ARTICLE).found is True


def test_curly_vs_straight_quotes_match():
    article = "She said “diversification is the durable strategy” to reporters."
    quote = 'diversification is the durable strategy'
    assert find_quote(quote, article).found is True


def test_apostrophe_curly_vs_straight():
    # Article has a curly apostrophe; student typed a straight one.
    quote = "President Trump's second term"
    assert find_quote(quote, ARTICLE.replace("'", "’")).found is True


def test_missing_quote_is_not_found():
    quote = "rare earth prices collapsed overnight"
    assert find_quote(quote, ARTICLE).found is False


def test_empty_article_cannot_verify():
    assert find_quote("anything at all", "").found is False


def test_empty_quote_is_not_found():
    assert find_quote("", ARTICLE).found is False
