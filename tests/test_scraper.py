"""Offline tests for the scraper's extraction + mapping logic."""

from datetime import date

from scraper.extract import (
    build_result,
    extract_from_html,
    _split_authors,
    _parse_date,
    normalize_author_name,
    looks_like_username,
    clean_title,
    parse_citation_authors,
)


# --- author name normalization (real data: JIED citation_author tags) ---

def test_normalize_author_name_last_first():
    # JIED publishes "Last, First" — render as "First Last".
    assert normalize_author_name("Pearson, Zoe") == "Zoe Pearson"
    assert normalize_author_name("Skiba, Alexandre") == "Alexandre Skiba"


def test_normalize_author_name_plain_unchanged():
    # Wilson Center already gives "First Last" — leave it alone.
    assert normalize_author_name("Aaron Korthuis") == "Aaron Korthuis"


def test_normalize_author_name_trims_whitespace():
    assert normalize_author_name("  McSweeney,  Kendra  ") == "Kendra McSweeney"


# --- username detection (real data: FP Analytics 'adamgriffiths') ---

def test_looks_like_username_flags_wordpress_handle():
    assert looks_like_username("adamgriffiths") is True
    assert looks_like_username("jsmith2") is True
    # trafilatura title-cases handles; a single jammed-together token is still
    # not a real "First Last" byline and must be flagged.
    assert looks_like_username("Adamgriffiths") is True


def test_looks_like_username_passes_real_names():
    assert looks_like_username("Aaron Korthuis") is False
    assert looks_like_username("Zoe Pearson") is False


# --- title suffix stripping (real data: "- FP Analytics", "| Journal of...") ---

def test_clean_title_strips_dash_sitename():
    assert (
        clean_title(
            "Fostering Resilience in Northern Central America - FP Analytics",
            "FP Analytics",
        )
        == "Fostering Resilience in Northern Central America"
    )


def test_clean_title_strips_pipe_sitename():
    assert (
        clean_title(
            "Acknowledging Cocaine Capital in Central American Development | "
            "Journal of Illicit Economies and Development",
            "Journal of Illicit Economies and Development",
        )
        == "Acknowledging Cocaine Capital in Central American Development"
    )


def test_clean_title_keeps_unrelated_separator():
    # A dash that isn't the sitename must survive untouched.
    assert (
        clean_title("Guns, Drugs - and Money in Honduras", "Wilson Center")
        == "Guns, Drugs - and Money in Honduras"
    )


def test_clean_title_no_publication_unchanged():
    assert clean_title("Some Title - Something", None) == "Some Title - Something"


# --- end-to-end mapping with the richer metadata ---

def test_build_result_prefers_citation_authors():
    meta = {
        "title": "Acknowledging Cocaine Capital | Journal of Illicit Economies and Development",
        "author": "Pearson; Zoe; Skiba; Alexandre",  # trafilatura's mangled guess
        "citation_authors": [
            "Pearson, Zoe",
            "Skiba, Alexandre",
            "McSweeney, Kendra",
            "Nielsen, Erik",
            "Piccorelli, Justin",
        ],
        "date": "2022-12-02",
        "sitename": "Journal of Illicit Economies and Development",
        "text": "Body.",
    }
    r = build_result(meta, "https://jied.lse.ac.uk/articles/10.31389/jied.110")
    assert r.citation.authors == [
        "Zoe Pearson",
        "Alexandre Skiba",
        "Kendra McSweeney",
        "Erik Nielsen",
        "Justin Piccorelli",
    ]
    assert r.citation.title == "Acknowledging Cocaine Capital"
    assert r.warnings == []


def test_build_result_warns_on_username_author():
    meta = {
        "title": "Fostering Resilience - FP Analytics",
        "author": "adamgriffiths",
        "date": "2021-09-01",
        "sitename": "FP Analytics",
        "text": "Body.",
    }
    r = build_result(meta, "https://fpanalytics.foreignpolicy.com/x/")
    # We keep the value (never invent) but flag it loudly.
    assert r.citation.authors == ["adamgriffiths"]
    assert any("username" in w.lower() for w in r.warnings)


def test_split_authors_variants():
    assert _split_authors(None) == []
    assert _split_authors("Jane Doe") == ["Jane Doe"]
    assert _split_authors("Jane Doe; John Roe") == ["Jane Doe", "John Roe"]
    assert _split_authors("Jane Doe and John Roe") == ["Jane Doe", "John Roe"]
    # Deduplicates repeats some sites emit.
    assert _split_authors("Jane Doe; Jane Doe") == ["Jane Doe"]


def test_parse_date():
    assert _parse_date("2026-01-15") == date(2026, 1, 15)
    assert _parse_date("2026-01-15T09:30:00Z") == date(2026, 1, 15)
    assert _parse_date(None) is None
    assert _parse_date("not a date") is None


def test_build_result_full():
    meta = {
        "title": "Some Headline",
        "author": "Jane Doe; John Roe",
        "date": "2026-01-15",
        "sitename": "Example Times",
        "hostname": "example.com",
        "text": "Body paragraph.",
    }
    r = build_result(meta, "https://example.com/a")
    c = r.citation
    assert c.authors == ["Jane Doe", "John Roe"]
    assert c.title == "Some Headline"
    assert c.publication == "Example Times"
    assert c.pub_date == date(2026, 1, 15)
    assert c.access_date == date.today()
    assert c.url == "https://example.com/a"
    assert r.article_text == "Body paragraph."
    assert r.warnings == []


def test_build_result_missing_fields_warn():
    r = build_result({"text": ""}, "https://example.com/a")
    joined = " ".join(r.warnings)
    assert "No author" in joined
    assert "No publication date" in joined
    assert "No article title" in joined
    assert "No article body" in joined
    # Citation still renders via the engine's placeholders.
    assert r.citation.author_string() == "No author provided"


def test_publication_falls_back_to_hostname():
    r = build_result({"hostname": "example.com", "text": "x"}, "https://example.com/a")
    assert r.citation.publication == "example.com"


SAMPLE_HTML = """
<!doctype html><html><head>
<meta property="og:title" content="Critical Minerals and Policy">
<meta property="og:site_name" content="Example Institute">
<meta name="author" content="Alex Researcher">
<meta property="article:published_time" content="2025-09-08">
</head><body>
<article>
<h1>Critical Minerals and Policy</h1>
<p>The supply chain for critical minerals has become a central policy concern
over the past several years, drawing attention from governments worldwide.</p>
<p>Analysts argue that diversification of sources is the most durable strategy
for reducing dependence on any single supplier nation going forward.</p>
</article></body></html>
"""


def test_parse_citation_authors_reads_meta_tags():
    html = (
        '<head>'
        '<meta name="citation_author" content="Pearson, Zoe">'
        "<meta name='citation_author' content='Skiba, Alexandre'>"
        '<meta name="citation_title" content="Irrelevant">'
        '</head>'
    )
    assert parse_citation_authors(html) == ["Pearson, Zoe", "Skiba, Alexandre"]


def test_parse_citation_authors_none_present():
    assert parse_citation_authors("<head></head>") == []


JOURNAL_HTML = """
<!doctype html><html><head>
<meta name="citation_title" content="Acknowledging Cocaine Capital | JIED">
<meta name="citation_author" content="Pearson, Zoe">
<meta name="citation_author" content="Skiba, Alexandre">
<meta property="og:site_name" content="Journal of Illicit Economies and Development">
<title>Acknowledging Cocaine Capital | Journal of Illicit Economies and Development</title>
</head><body><article>
<h1>Acknowledging Cocaine Capital</h1>
<p>Sustained body paragraph text that is long enough to be extracted by the
parser as the main article content for verbatim checking later on.</p>
</article></body></html>
"""


def test_extract_from_html_uses_citation_authors():
    r = extract_from_html(JOURNAL_HTML, "https://jied.lse.ac.uk/x")
    assert r.citation.authors == ["Zoe Pearson", "Alexandre Skiba"]


def test_extract_from_html_fixture_offline():
    r = extract_from_html(SAMPLE_HTML, "https://example.org/minerals")
    c = r.citation
    assert c.title == "Critical Minerals and Policy"
    assert "Alex Researcher" in c.authors
    assert c.pub_date == date(2025, 9, 8)
    assert len(r.article_text) > 50
