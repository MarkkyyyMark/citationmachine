# Pilot web app spec

The internet-accessible tool: a student pastes an article **URL** + the
**quote** they want, reviews/corrects the scraped fields, and copies a finished
Stoa evidence card. Citation format contract: [`citation-format-spec.md`](citation-format-spec.md).
Confirmed with the user 2026-06-02/03.

## Principles

- **Exact-from-source.** Author, date, title, publisher, URL come straight from
  the page and are never invented. The student confirms/edits before use.
- **Flag, don't guess.** Low-confidence fields (username-looking authors,
  missing date, quote-not-found) surface as warnings, not silent values.
- **One formatter.** All rendering goes through the existing Python
  `citation_engine`; the frontend never re-implements formatting.

## Architecture

**Backend — FastAPI**, reusing `citation_engine` + `scraper` unchanged.

| Endpoint | In | Out |
|---|---|---|
| `POST /api/scrape` | `{url, quote}` | scraped fields + warnings + verbatim result |
| `POST /api/credentials` | `{authors, publication, url}` | `{short_credential, qualifications}` AI draft |
| `POST /api/format` | all (edited) fields | `{plain, html}` |
| `GET /` | — | single-page frontend |

`/api/credentials` is separate so the form returns immediately and the
(slower) credential draft streams in afterward.

**Frontend — single page, two columns.** Left: editable fields + inline
warnings. Right: live citation preview (calls `/api/format`, debounced ~400ms
on edit) + two copy buttons — "Copy for Google Docs" writes the rendered HTML
to the clipboard (`text/html`, bold survives); "Copy plain" writes plain text.
Plain HTML/CSS/JS, polished with the frontend-design skill.

## New modules

- `verify/verbatim.py` — pure. `find_quote(quote, article_text)` →
  found / not-found, after normalizing whitespace and curly vs straight quotes.
  Drives the "quote not found in article — verify" warning. Free, TDD'd.
- `credentials/drafter.py` — Claude (Anthropic SDK) **with the web-search tool**
  to find the author's real credentials, then draft a short credential (for the
  bold lead) + a fuller qualifications sentence. Always returned as a draft the
  student reviews; never written as final. Uses prompt caching. Key from env.
- `webapp/` — FastAPI app (`main.py`) + `static/` frontend.

## Data flow

1. Student submits URL + quote.
2. `/api/scrape`: fetch → extract → Citation fields + warnings; verbatim check
   adds a warning if the quote isn't found in the article body.
3. Frontend fills fields, shows warnings, and fires `/api/credentials` in the
   background → fills the credential fields with the AI draft, flagged "verify."
4. Any field edit → debounced `/api/format` → live preview updates.
5. Student copies (Docs HTML or plain).

## Secrets

`ANTHROPIC_API_KEY` loaded from a gitignored `.env` (python-dotenv). The user
puts the real key there; it never enters git or chat. `/api/credentials`
returns a clear error if the key is missing, and the rest of the app still
works (manual credential entry).

## Build order

1. **Verbatim checker** — pure, free, test-first.
2. **Core web app** — `/api/scrape` + `/api/format` + two-column frontend with
   live preview + copy. Usable pilot on its own.
3. **Credential drafter** — `/api/credentials` + Anthropic web-search draft,
   wired into the UI.
4. **Deploy to Render** — later.

## Out of scope (pilot)

PDF sources (DTIC-style), student accounts/logins, persistence/history. Deploy
hardening (rate limits) comes with step 4.
