"""Draft author credentials with Claude + web search.

Credentials are the one citation field that isn't on the article page, so they
can't be scraped. We ask Claude to search the web for the author's real
credentials and draft two things:

  - short_credential: a brief phrase for the bold lead (e.g. "Director of the
    Critical Minerals Security Program at CSIS")
  - qualifications:  a fuller sentence for the parenthetical

The result is ALWAYS a draft the student reviews — never written as final, and
never fabricated. If Claude can't verify a credential, it returns empty strings.

Pure helpers (build_user_prompt, parse_credentials) are unit-tested; the live
call (draft_credentials) needs ANTHROPIC_API_KEY from the environment / .env.
"""

from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv

load_dotenv()  # pull ANTHROPIC_API_KEY from a local .env if present

# Defer TLS verification to the OS certificate store so the Anthropic client
# trusts certs injected by school / corporate / antivirus TLS-intercepting
# proxies. Without this, httpx rejects them with "unable to get local issuer
# certificate" and every API call fails. Mirrors scraper/fetch.py; idempotent.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:  # pragma: no cover - truststore is a hard runtime dep
    pass

MODEL = "claude-opus-4-8"

_SYSTEM = (
    "You research and draft author credentials for high-school debate evidence "
    "citations. You are given the LEAD author to focus on (plus any co-authors "
    "for context), the publication, and the article URL. A citation names one "
    "author — the lead — so draft credentials for THAT person. Use web search "
    "to find their REAL, current credentials relevant to the article's subject "
    "— their title, role, and affiliation.\n\n"
    "Return ONLY a JSON object with exactly these keys:\n"
    '  "short_credential": a brief phrase for a citation\'s bold lead, e.g. '
    '"Director of the Critical Minerals Security Program at CSIS". No name, no '
    "trailing period.\n"
    '  "qualifications": one complete sentence describing the credentials, e.g. '
    '"Dr. Gracelin Baskaran is director of the Critical Minerals Security '
    'Program at the Center for Strategic and International Studies (CSIS)."\n'
    '  "verified": true if you confirmed these credentials from a reputable '
    "source via web search; false if this is your best-effort guess from the "
    "author's name, the publication, and general knowledge.\n\n"
    "Always give the student SOMETHING to check — never return empty strings if "
    "you can produce even a plausible best-effort credential (e.g. inferring an "
    'affiliation from the publication). Set "verified": false whenever you are '
    "not certain. NEVER present a guess as verified — an unchecked wrong "
    "credential in a citation is worse than one the student knows to double-"
    "check. Only fall back to empty strings if you genuinely have nothing at all "
    "to offer, not even an inference."
)


def build_user_prompt(authors: list[str], publication: str | None, url: str) -> str:
    """The per-request instruction (kept out of the cached system prompt).

    Names the lead (first) author as the target — that's who a citation cites —
    and lists any co-authors only as context.
    """
    if authors:
        lead = authors[0]
        lead_line = f"Lead author (draft credentials for this person, the one we cite): {lead}"
        others = authors[1:]
        coauthor_line = f"\nCo-authors (context only): {', '.join(others)}" if others else ""
    else:
        lead_line = f"Lead author: (no named author; publisher: {publication})"
        coauthor_line = ""
    return (
        f"{lead_line}{coauthor_line}\n"
        f"Publication: {publication or 'unknown'}\n"
        f"Article URL: {url}\n\n"
        "Find the lead author's credentials and return the JSON object."
    )


def parse_credentials(text: str) -> dict:
    """Extract the {short_credential, qualifications} JSON from Claude's reply."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise CredentialError("No JSON object found in the model response.")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise CredentialError(f"Could not parse credential JSON: {exc}") from exc
    return {
        "short_credential": (data.get("short_credential") or "").strip(),
        "qualifications": (data.get("qualifications") or "").strip(),
        # Default to unverified: a reply that omits the flag is treated as a best
        # guess, so the UI always tells the student to double-check.
        "verified": bool(data.get("verified", False)),
    }


class CredentialError(Exception):
    """Raised when credentials cannot be drafted (no key, API error, bad output).

    ``retryable`` is True when the failure is transient (timeout, connection
    blip, 5xx/overload) and a fresh attempt is likely to succeed — the web layer
    uses it to tell the student "try again" rather than "enter manually".
    """

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def is_transient(exc: Exception) -> bool:
    """Would retrying this error plausibly succeed?

    Timeouts and connection errors are always transient; HTTP errors are
    transient only for 5xx / 529 overload (a 4xx is a real request problem that
    won't fix itself). Classified by name + status_code so we don't depend on
    constructing the SDK's exception classes.
    """
    name = type(exc).__name__
    if name in {"APITimeoutError", "APIConnectionError"}:
        return True
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and status >= 500


def draft_credentials(authors: list[str], publication: str | None, url: str) -> dict:
    """Call Claude with web search and return drafted credentials.

    Raises CredentialError when the API key is missing or the call fails, so the
    web layer can fall back to manual entry without crashing.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise CredentialError("ANTHROPIC_API_KEY is not set.")

    import anthropic

    # Bound the call so a hung web search can't pin the single free-tier worker.
    # Retries: the SDK auto-retries timeouts / 5xx / 429 with exponential
    # backoff, so allow a few — a single transient blip was surfacing to the
    # student as a hard "unavailable" even though a retry would have worked.
    timeout = float(os.environ.get("CREDENTIALS_TIMEOUT", "90"))
    retries = int(os.environ.get("CREDENTIALS_RETRIES", "3"))
    client = anthropic.Anthropic(timeout=timeout, max_retries=retries)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            thinking={"type": "adaptive"},
            system=[
                {"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}
            ],
            tools=[{"type": "web_search_20260209", "name": "web_search"}],
            messages=[{"role": "user", "content": build_user_prompt(authors, publication, url)}],
        )
    except anthropic.APIError as exc:
        # Flag transient failures so the UI can say "try again" instead of
        # sending the student to manual entry for a momentary blip.
        raise CredentialError(
            f"Claude request failed: {exc}", retryable=is_transient(exc)
        ) from exc

    text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
    return parse_credentials(text)
