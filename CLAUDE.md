# Citation Machine — working contract

A web app that turns an article URL + a quote into a **Stoa debate evidence card**.
Built for high-school debaters. The exact card format is the product; get it wrong
and the tool is useless.

## What it must always do (the non-negotiables)
- **Never fabricate.** Author names, dates, credentials, quotes — everything is
  either scraped/verified or clearly flagged for the student to confirm. A wrong
  credential in a citation is academic dishonesty; that risk outranks convenience.
- **The student verifies every field.** The UI is edit-first: we pre-fill, they confirm.
- **The card format is frozen.** The exact wording/order lives in
  `docs/citation-format-spec.md`. Change the formatter only against that spec,
  and keep the formatter tests green — they encode the contract.

## Architecture (keep these boundaries)
Layered so the logic is testable without network or a browser:
- `citation_engine/` — pure formatting (Citation model → card). No network, no I/O.
- `scraper/` — `fetch.py` (HTTP) + `extract.py` (trafilatura → fields). Network lives here.
- `verify/` — verbatim quote checker (is the quote actually on the page).
- `credentials/` — `drafter.py`: the ONE paid path (Claude + web search) to draft the
  lead author's credentials. Returns `{short_credential, qualifications, verified}`.
- `webapp/` — FastAPI: `/api/scrape`, `/api/format`, `/api/credentials`, `/` (SPA).
  `schemas.py` = request/response contracts + input caps. `ratelimit.py` = per-IP caps.
- `webapp/static/` — vanilla HTML/CSS/JS, no framework, no build step.

**Rule:** pure logic never imports network code. New judgment logic (what to trust,
how to title) belongs in a pure, unit-tested function — not buried in the web layer.

## Conventions that bite if ignored
- **Escape all HTML output** — both `formatter.py` (via `html.escape`) and `app.js`
  (via `escapeHtml`). User/scraped text is untrusted.
- **`ratelimit.client_ip` keys on the LAST X-Forwarded-For hop** (the proxy-appended
  one). Never trust the first hop — it's forgeable and would defeat the cap on the
  billable endpoint.
- **`credentials/drafter.py` is the only code that spends money.** Model, thinking,
  and web-search-tool params must match the current Anthropic API (verify against the
  claude-api skill before changing them — don't trust memory). It retries transient
  errors and flags them `retryable` so the UI says "try again" vs "enter manually".
- **`schemas._AUTHORS_MAX`** caps the author list; real think-tank/academic pieces
  have 10-30 authors, so keep it generous (currently 40) — a low cap silently 422s
  legitimate multi-author pages.
- **Static assets are cache-busted** by `index()` (injects `?v=<hash>`). Don't
  hardcode `/static/app.js` without going through `index()`, or testers run stale JS.

## Run / test / deploy
- Run locally: `.venv/Scripts/python -m uvicorn webapp.main:app --port 8000`
- Test: `.venv/Scripts/python -m pytest -q` (offline; the live Claude/HTTP calls are
  NOT unit-tested — pure helpers and degraded paths are). Keep the suite green.
- Deploy: Render Blueprint (`render.yaml`). `ANTHROPIC_API_KEY` is set in the Render
  dashboard, never committed. `.env` (local key) is gitignored.
- Deps are pinned in `requirements.txt` — bump deliberately, don't loosen to `>=`.

## Verifying a change (before claiming it works)
Exercise the real path, not just tests. For a UI/endpoint change, run the app and hit
the actual endpoint with a realistic payload (e.g. a multi-author page for
`/api/credentials`). Testing a helper in isolation missed a real 422 once — reproduce
at the boundary that actually fails.
