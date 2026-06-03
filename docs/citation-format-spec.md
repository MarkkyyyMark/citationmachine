# Citation format spec

The exact-wording contract for a rendered evidence card. Confirmed with the
user 2026-06-02 against the Nile Critical Minerals brief.

## Structure (one block)

```
<LEAD>. [(<qualifications>) ]"<title>" <publisher>, <full published date>. Accessed <today> <url>
    <verbatim quote, double-indented>
```

- **LEAD** (the only **bold** part): `<identifier>, [<middle>, ]<Month Year>`
  - `identifier` = the author(s) if present, else the publisher.
  - `middle` = `No author provided` when there is no author; otherwise the
    author's **short credential** if we have one; otherwise omitted.
  - date in the lead is **month + year only** (e.g. `January 2026`).
  - LEAD ends with a period.
- **(qualifications)** — the full drafted author/publisher bio, in parentheses.
  Omitted when we have none. AI-drafted + human-reviewed (Phase 4).
- **"title"** — in double quotes.
- **publisher, full published date.** — the **full** date (`January 15, 2026`)
  lives here, with the publisher, ending in a period.
- **Accessed `<today>`** — the access date is the day the student pulls the
  citation (the scraper sets it to today).
- **url** — plain, exact.
- **quote** — verbatim, double-indented, no styling (the student underlines the
  portion they read aloud).

## Emphasis

Only the LEAD is bold. No italics. The single underline in real briefs is the
URL being a live hyperlink. Output is HTML so the bold survives copy-paste into
Google Docs; selecting and copying the rendered card pastes formatted.

## Exactness

Author, date, title, publisher, and URL are passed through verbatim from the
source — never edited or invented. The publisher shown in the lead and in the
date line is the same scraped value (we do not coin a display name). When a
field is genuinely unavailable, the Stoa placeholders are used:
`No author provided`, `No publication date available`.

## Worked examples

**With author + credentials** (Baskaran, pulled 2026-06-02):

> **Gracelin Baskaran, Director of the Critical Minerals Security Program at
> CSIS, January 2026.** (Dr. Gracelin Baskaran is director of the Critical
> Minerals Security Program at the Center for Strategic and International
> Studies (CSIS)) "New Executive Order Ties U.S. Critical Minerals Security to
> Global Partnerships" CSIS, January 15, 2026. Accessed January 20, 2026
> https://www.csis.org/...
> &nbsp;&nbsp;&nbsp;&nbsp;During President Trump's second term, critical
> minerals have emerged as a prominent element of U.S. foreign policy.

**No author** (DFC):

> **DFC.gov, No author provided, December 2025.** "DFC Secures Expanded
> Authorities with FY26 NDAA Signed into Law" DFC.gov, December 18, 2025.
> Accessed June 2, 2026 https://www.dfc.gov/...
> &nbsp;&nbsp;&nbsp;&nbsp;[quote, double-indented]
