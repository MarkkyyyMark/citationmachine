"""Tests for the credential drafter's pure helpers.

The live Claude web-search call is not unit-tested (needs a key); the
prompt-building and JSON-parsing logic is.
"""

import pytest

from credentials.drafter import (
    build_user_prompt,
    parse_credentials,
    CredentialError,
    is_transient,
)


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


# --- best-effort drafting: always return something, flagged verified/unverified ---

def test_parse_credentials_reports_verified_flag():
    text = '{"short_credential": "Director at CSIS", "qualifications": "Dr. X is director at CSIS.", "verified": true}'
    out = parse_credentials(text)
    assert out["verified"] is True


def test_parse_credentials_verified_defaults_false_when_absent():
    # A model reply without the flag is treated as an unverified best guess —
    # safer to over-flag "check this" than to imply verification that didn't happen.
    out = parse_credentials('{"short_credential": "Analyst at CSIS", "qualifications": "X is an analyst."}')
    assert out["verified"] is False


class _FakeExc(Exception):
    """Stand-in for an anthropic error without constructing the real SDK class."""
    def __init__(self, name, status_code=None):
        super().__init__(name)
        self.__class__.__name__ = name
        if status_code is not None:
            self.status_code = status_code


def test_is_transient_flags_timeouts_and_5xx():
    # These are the intermittent failures that should be retried / surfaced as
    # "try again", not "enter manually".
    assert is_transient(_FakeExc("APITimeoutError")) is True
    assert is_transient(_FakeExc("APIConnectionError")) is True
    assert is_transient(_FakeExc("InternalServerError", status_code=500)) is True
    assert is_transient(_FakeExc("OverloadedError", status_code=529)) is True


def test_is_transient_false_for_client_errors():
    # A 400/401 won't fix itself on retry — that's a real config problem.
    assert is_transient(_FakeExc("BadRequestError", status_code=400)) is False
    assert is_transient(_FakeExc("AuthenticationError", status_code=401)) is False


def test_build_user_prompt_designates_lead_author():
    # We cite one author per evidence card — the lead (first) author. The prompt
    # must name that person as the target even when the page lists many.
    p = build_user_prompt(
        ["Seth G. Jones", "Riley McCabe", "Yasir Atalan"], "CSIS", "https://csis.org/x"
    )
    assert "Seth G. Jones" in p
    # The lead author must be identified as the one to draft, not buried in a list.
    lead_line = next(line for line in p.splitlines() if "Seth G. Jones" in line)
    assert "lead" in lead_line.lower() or "cite" in lead_line.lower()
