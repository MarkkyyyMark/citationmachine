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
    "citations. You are given an author (or none), the publication, and the "
    "article URL. Use web search to find the author's REAL, current credentials "
    "relevant to the article's subject — their title, role, and affiliation.\n\n"
    "Return ONLY a JSON object with exactly these keys:\n"
    '  "short_credential": a brief phrase for a citation\'s bold lead, e.g. '
    '"Director of the Critical Minerals Security Program at CSIS". No name, no '
    "trailing period.\n"
    '  "qualifications": one complete sentence describing the credentials, e.g. '
    '"Dr. Gracelin Baskaran is director of the Critical Minerals Security '
    'Program at the Center for Strategic and International Studies (CSIS)."\n\n'
    "Rules: Never invent or guess. If you cannot verify a credential from a "
    "reputable source, return empty strings for both keys. These are drafts a "
    "student will verify — accuracy matters far more than completeness."
)


def build_user_prompt(authors: list[str], publication: str | None, url: str) -> str:
    """The per-request instruction (kept out of the cached system prompt)."""
    who = ", ".join(authors) if authors else f"(no named author; publisher: {publication})"
    return (
        f"Author: {who}\n"
        f"Publication: {publication or 'unknown'}\n"
        f"Article URL: {url}\n\n"
        "Find this author's credentials and return the JSON object."
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
    }


class CredentialError(Exception):
    """Raised when credentials cannot be drafted (no key, API error, bad output)."""


def draft_credentials(authors: list[str], publication: str | None, url: str) -> dict:
    """Call Claude with web search and return drafted credentials.

    Raises CredentialError when the API key is missing or the call fails, so the
    web layer can fall back to manual entry without crashing.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise CredentialError("ANTHROPIC_API_KEY is not set.")

    import anthropic

    # Bound the call so a hung web search can't pin the single free-tier worker.
    # Retries stay low for the same reason; the UI falls back to manual entry.
    timeout = float(os.environ.get("CREDENTIALS_TIMEOUT", "90"))
    client = anthropic.Anthropic(timeout=timeout, max_retries=1)
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
        raise CredentialError(f"Claude request failed: {exc}") from exc

    text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
    return parse_credentials(text)
