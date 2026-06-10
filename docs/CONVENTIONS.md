# Conventions

These are the working rules for the dataset. They exist so the data stays trustworthy
and the website stays copyright-safe. When in doubt, prefer accuracy over completeness.

## Golden rules

1. **Never invent data.** If a value is unknown, enter `-` and leave it for verification.
   A blank is always better than a guess.
2. **Preserve the schema and IDs exactly.** Don't rename columns or reuse IDs. A
   performer keeps one `queen_id` across every season.
3. **Cite sources for new data.** Primary sources preferred: the season's Wikipedia
   page and individual episode pages; Fandom season pages; Paramount+ synopses.
4. **One season at a time**, verified end-to-end before moving on.
5. **Original visual identity only.** No official logos, trade dress, or contestant
   photos; no social-media handles. Names and outbound links are fine.

## Derived vs. entered

Some columns are **computed**, never hand-typed. If you change the underlying data,
re-run the build and let `validate.py` confirm:

- `contestants.wins / highs / lows / bottoms` ← counted from `progression`
  (`bottoms = BTM + ELIM`).
- `songs.times_used` ← distinct episodes a song appears in.
- The entire `derived` block in `site_data.js`.

## Controlled vocabularies

- **progression.status**: `WIN`, `HIGH`, `SAFE`, `LOW`, `BTM`, `ELIM`, `WINNER`,
  `RUNNER-UP`, `RTRN`, `GUEST`, `SURVIVAL`/`STAY`, `IMM`, `WDR`, `DISQ`.
  - Early seasons didn't always distinguish HIGH/LOW on screen — record what's
    verifiable; use `SAFE` (or `-`) where the distinction is genuinely unknown.
- **episodes.main_challenge_type**: Acting, Design, Girl Group, Makeover, Snatch Game,
  Comedy, Singing, Song-Verse, Talent Show, Finale, Reunion, Clip Show.
- **lip_syncs.result_type**: NORMAL, SURVIVAL, SHANTAY, SASHAY, TOPS, CROWN
  (see [DATA_MODEL.md](DATA_MODEL.md) for what each means).
- **elimination_events.event_type**: eliminated, returned, withdrew, disqualified,
  saved-no-elimination, reversed.

## Known judgment calls (carried in the data today)

- **Willam, S4E8** is recorded as a challenge `WIN` in `progression`; the
  disqualification lives in `elimination_events` only (overwriting the win would
  undercount his challenge wins versus the official record).
- A returnee has **two** elimination episodes; both are `ELIM` in `progression`, with the
  return captured as a `returned` row in `elimination_events`.
- `elimination_events.event_type` uses `eliminated` for S1–S14 and `LSFYL elimination`
  for S15–S18 — a vocabulary drift that is a candidate for future unification.
- A short list of S5–S18 song-pointer conflicts (multi-lip-sync finales / LaLaPaRuZa
  episodes, two genuinely different songs, and the S18 blank-lip-sync gaps) is left for
  source review rather than guessed. See [CHANGELOG.md](../CHANGELOG.md).

## Visual identity (for `site/`)

- Palette "pageant-noir": hot magenta `#e6007e`, gold `#f4b53f`, deep purple `#2a0e3a`,
  glam cream. Display font Bodoni Moda; mono Space Mono.
- Hand-drawn SVG icons: crown = winner, lipstick = lip sync, star = power-up/save,
  sash = Miss Congeniality.
