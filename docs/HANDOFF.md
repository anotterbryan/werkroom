# Project Handoff

**Owner:** Bryan · **Scope:** RuPaul's Drag Race US main series, Seasons 1–18
**Status:** Repository established with a reproducible build + validation pipeline.
S1–S4 verified against primary sources; S5–S18 carried forward from the prior
lip-sync rebuild (validated, pending a season-by-season content pass).

---

## What this is

A relational database of *RuPaul's Drag Race* (US main, S1–S18) that powers an original,
copyright-safe data-visualization website of ~30 views. The CSVs in `data/` are the
source of truth; the website, JSON, and workbook are generated from them.

## How it fits together

```
data/*.csv ──build_site_data.py──▶ site/site_data.js  ◀──loaded by──  site/index.html
        │                                    (global DATA)        (all views; edit this)
        ├──build_xlsx.py──▶ dist/DragRaceDB_master.xlsx
        └──validate.py (CI gate: 31 invariants)
```

Editing data never touches view code, and editing views never touches data — the build
only regenerates the data file the page loads. See [README](../README.md) for commands.

## Current row counts

| table | rows |  | table | rows |
|---|---|---|---|---|
| queens | 238 |  | songs | 260 |
| seasons | 18 |  | lip_syncs | 270 |
| contestants | 242 |  | elimination_events | 186 |
| episodes | 255 |  | panel | 74 |
| progression | 2021 |  | appearances | 395 |

## Done

- **S1–S4 verified** against Wikipedia/episode pages: air dates, challenge names + types,
  some runway themes, several title corrections; added `home_city`; filled entrance
  orders; reconciled five blank `eliminated_id`s; merged 21 duplicate/typo song rows;
  upgraded the S1–S4 progression vocabulary (ELIM / WINNER / RUNNER-UP) and recomputed
  tallies. The tally formula now holds with **0 mismatches across all 18 seasons**.
- **Repository + pipeline** built and validated: `build_site_data.py` reproduces every
  derived table byte-for-byte on unchanged inputs (incl. the assassin board);
  the site loads `site_data.js` at runtime, so a data rebuild never touches `index.html`
  or the view code; `validate.py` passes 31/31; `build_xlsx.py` mirrors the CSVs.

## Open items (roughly in order)

1. **S5–S10, then S10–S18** season-by-season verification pass (the main remaining work).
2. Resolve the flagged S5–S18 song-pointer conflicts (multi-lip-sync finales/LaLaPaRuZa,
   two genuine different-song conflicts, S18 blank lip-sync songs). See CHANGELOG.
3. Decide whether to unify `elimination_events.event_type` ("eliminated" vs
   "LSFYL elimination") across seasons.
4. A couple of S1–S4 runway-name conflicts noted during verification (S2E3, S4E5).
5. Deploy to **GitHub Pages**; add **bracket generation** for LaLaPaRuZa/crown smackdowns.
6. **All Stars + international franchises** as a future expansion (extends returning-queen
   and connection views significantly).

## Working notes

- The scratch workspace used to assemble this repo is non-persistent; this repository is
  now the durable home — clone it and work from `data/`.
- Source PDFs/screenshots used for verification are intentionally **not** committed
  (copyright); keep them in a local, untracked `reference/` folder if useful.
