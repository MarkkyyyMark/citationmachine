"""Per-IP rate limiting for the public endpoints (Phase 7 hardening).

The credential endpoint makes billable Claude + web-search calls, so it gets the
tightest cap. Scraping does a live fetch and gets a looser one. Formatting is
local and cheap and is left unlimited (it fires on every keystroke).

Limits are read from the environment at request time so they can be tuned on the
host without a code change (and so tests can swap them). Values use the `limits`
syntax, e.g. "10/hour" or "10/hour;3/minute".
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def client_ip(request: Request) -> str:
    """The real visitor's IP.

    Render (and most hosts) sit behind a proxy, so ``request.client.host`` is the
    proxy's address — every visitor would share one bucket. The real client is
    the first hop in ``X-Forwarded-For``; fall back to the socket peer locally.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip)


def credentials_limit() -> str:
    """Tightest cap — the billable Claude + web-search endpoint."""
    return os.environ.get("RATE_CREDENTIALS", "10/hour;3/minute")


def scrape_limit() -> str:
    """Looser cap — a live fetch, but free."""
    return os.environ.get("RATE_SCRAPE", "30/minute")
