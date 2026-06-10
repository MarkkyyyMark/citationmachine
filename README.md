# Citation Machine

A web tool for Stoa Team Policy debaters: paste an article **URL** and the
**passage** you want to quote, and it produces a properly formatted evidence
card — author, qualifications, title, date, access date, and URL — matching the
Stoa citation standards and the Nile brief format.

## Citation format (the spec)

Driven by two Stoa documents:

- **Team Policy Debate Rules 2022-23**, §H.2.b — required citation parts.
- **Evidence Philosophy and Standards 2024-25**, §I.3 — complete source
  citation, including the "strongly encouraged" author qualifications.

A complete card looks like (the **bold lead** is the only emphasized part):

```
**Author, short credential, Month Year.** (full qualifications) "Article Title"
Publisher, Month D, YYYY. Accessed Month D, YYYY https://example.com/article
    Verbatim quoted text, first word of a sentence to ending punctuation,
    double-indented to differentiate evidence from non-evidence.
```

The lead carries month + year; the full published date appears in the body with
the publisher; the access date is the day the student pulls the citation.
No-author cards lead with the publisher. The exact-wording contract — confirmed
against the Nile brief — is in [`docs/citation-format-spec.md`](docs/citation-format-spec.md).

When a field is genuinely unavailable, the Stoa-required placeholders are used:
`No author provided`, `No publication date available`.

## Build plan

| Phase | What | Cost / keys |
|---|---|---|
| 1 | Citation engine (format + tests) | Free, local — **done** |
| 2 | Scraper + metadata extraction (author, date, title, publication) | Free, local — **done** |
| 3 | Verbatim + contiguity verifier; `#:~:text=` deep links | Free, local |
| 4 | Author-qualification finder (web search + LLM draft) | Anthropic API key |
| 5 | Web app (FastAPI API + form + editable results + export) | Free, local |
| 6 | Public deploy (Render) | Hosting account |
| 7 | Hardening: per-IP rate limits, input caps, call timeout, credential UX | Free, local — **done** |

The qualification finder (Phase 4) **drafts** a bio for the student to review;
it never silently auto-fills, because credentials aren't on the article page and
must be verified by a human.

## Layout

```
citation_engine/      # Phase 1 — pure logic, no network
  models.py           #   Citation dataclass (fields = Stoa requirements)
  formatter.py        #   renders the card: plain text + HTML (bold lead)
docs/                 # citation-format-spec.md — exact-wording contract
scraper/              # Phase 2 — fetch + metadata extraction
  fetch.py            #   GET html; truststore for proxied/AV networks
  extract.py          #   trafilatura + citation_author tags -> Citation
verify/               # verbatim quote checker (is the quote in the article?)
credentials/          # Phase 4 — Claude web-search credential drafter
webapp/               # Phase 5 — FastAPI API + two-column frontend
  main.py             #   /api/scrape, /api/format, /api/credentials, /
  static/             #   index.html, style.css, app.js
tests/                # anchored to the real Nile/Stoa examples
demo.py               # prints a sample card
```

The scraper was verified live against real debate sources (Wilson Center, FP
Analytics, the JIED journal). Two lessons baked into the code: prefer the
`citation_author` meta tags publishers emit (exact names, no guessing), and
flag low-confidence fields loudly rather than trust them — extraction is never
100%, so a human confirms before the citation is final.

## Develop

```
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -r requirements-dev.txt
.venv/Scripts/python -m pytest -q
.venv/Scripts/python demo.py
```

## Run the web app

```
.venv/Scripts/python -m uvicorn webapp.main:app --reload
```

Then open http://127.0.0.1:8000 — paste a URL + quote, review the fields, copy
the citation. Author-credential drafting needs an Anthropic API key: copy
`.env.example` to `.env` and set `ANTHROPIC_API_KEY`. Without a key the app
still works; you enter credentials by hand.

## Deploy (Render)

[`render.yaml`](render.yaml) defines the service. On Render: **New → Blueprint**,
point it at this GitHub repo, and it reads the build/start commands and the
pinned Python version automatically. The one thing the blueprint can't carry is
the secret — add `ANTHROPIC_API_KEY` in the service's **Environment** settings.
Without it the site still runs; credential drafting falls back to manual entry.

The free tier sleeps after ~15 min idle, so the first request after a quiet
spell takes ~30–60s to wake. The credential endpoint is rate-limited per IP
(Phase 7) since it makes billable Claude + web-search calls; tune the caps with
`RATE_CREDENTIALS` / `RATE_SCRAPE` env vars (see `.env.example`) without a
redeploy.
