"""Tests for the credential drafter's pure helpers.

The live Claude web-search call is not unit-tested (needs a key); the
prompt-building and JSON-parsing logic is.
"""

import pytest

from credentials.drafter import build_user_prompt, parse_credentials, CredentialError


def test_build_user_prompt_includes_author_and_publication():
    p = build_user_prompt(["Gracelin Baskaran"], "CSIS", "https://csis.org/x")
    assert "Gracelin Baskaran" in p
    assert "CSIS" in p
    assert "https://csis.org/x" in p


def test_build_user_prompt_handles_no_author():
    p = build_user_prompt([], "DFC.gov", "https://dfc.gov/x")
    assert "DFC.gov" in p


def test_parse_credentials_plain_json():
    text = '{"short_credential": "Director at CSIS", "qualifications": "Dr. X is director at CSIS."}'
    out = parse_credentials(text)
    assert out["short_credential"] == "Director at CSIS"
    assert out["qualifications"] == "Dr. X is director at CSIS."


def test_parse_credentials_in_code_fence():
    text = (
        "Here is the result:\n```json\n"
        '{"short_credential": "Energy reporter at CNBC", "qualifications": "Spencer is an energy reporter at CNBC."}'
        "\n```\n"
    )
    out = parse_credentials(text)
    assert out["short_credential"] == "Energy reporter at CNBC"


def test_parse_credentials_missing_keys_default_to_empty():
    out = parse_credentials('{"short_credential": "Analyst"}')
    assert out["short_credential"] == "Analyst"
    assert out["qualifications"] == ""


def test_parse_credentials_no_json_raises():
    with pytest.raises(CredentialError):
        parse_credentials("I could not find any credentials for this author.")
