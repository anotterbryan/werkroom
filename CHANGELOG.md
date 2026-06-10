# Changelog

All notable changes to the dataset and tooling. Dates are `YYYY-MM-DD`.

## [Unreleased]

### Added
- **Repository + reproducible build pipeline.** Data and view code are kept in separate
  files: `data/*.csv` → `scripts/build_site_data.py` → `site/site_data.js`, which
  `site/index.html` loads at runtime via `<script src="site_data.js">`. Regenerating data
  rewrites only `site_data.js` and never touches `index.html` or the views. A frozen
  self-contained snapshot is kept at `site/index.embedded.html` as an offline fallback.
- `scripts/validate.py` — 31-check invariant suite (PK/FK integrity, ground-truth
  reconciliation, tally formula, `times_used`) wired into CI.
- `scripts/build_xlsx.py` — regenerates `dist/DragRaceDB_master.xlsx` from the CSVs.
- `docs/DATA_MODEL.md`, `docs/CONVENTIONS.md`, `docs/HANDOFF.md`; `LICENSE` (MIT, code),
  `DATA_LICENSE.md` (CC BY-SA 4.0, data), GitHub Actions for validation + Pages.
- `contestants.home_city` column (per-season location, distinct from `queens.hometown`).

### Changed — Seasons 1–4 verification (against Wikipedia + episode pages)
- Filled S1–S4 air dates, main-challenge names and types, and several runway themes;
  corrected a few episode titles.
- Filled S1–S4 entrance orders where sourced.
- Reconciled five previously-blank `eliminated_id`s (US05E02, US10E11, US11E07, US12E09,
  US14E11) against the validated lip-sync + progression data, and added matching
  `elimination_events` rows.
- Merged 21 duplicate / typo song rows (e.g. "Hex Rector" → "Hex Hector"), repointing
  `episodes` to the canonical `lip_syncs` song and recomputing `times_used`
  (songs 286 → 260).
- Upgraded the S1–S4 `progression` vocabulary (added `ELIM`, `WINNER`, `RUNNER-UP`) and
  recomputed `contestants` tallies. **The tally formula now holds with 0 mismatches
  across all 18 seasons.**

### Known open items (see docs/HANDOFF.md)
- **S5–S18 song-pointer conflicts left for source review** (not guessed):
  - Multi-lip-sync episodes where `episodes.lip_sync_song_id` is one of several songs
    (finales / LaLaPaRuZa): US09E14, US10E14, US11E14, US15E08, US16E15, US17E15.
  - Two genuine different-song conflicts: US14E03 ("I Love It" — Kylie Minogue vs
    Icona Pop) and US17E16 ("Training Season" vs "Abracadabra").
  - S18 blank lip-sync songs: US18E11, US18E14.
- **Willam, S4E8** recorded as a challenge `WIN`; the disqualification is captured in
  `elimination_events` only (a deliberate call to avoid undercounting his wins).
- `elimination_events.event_type` drift: `eliminated` (S1–S14) vs `LSFYL elimination`
  (S15–S18) — candidate for unification.
- Two S1–S4 runway-name conflicts noted but not overwritten (S2E3, S4E5).

### Notes
- Licensing (MIT for code, CC BY-SA 4.0 for data) is a sensible default given the
  Wikipedia sourcing, but confirm before publishing and set your name in `LICENSE`.
