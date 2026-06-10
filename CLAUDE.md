# CLAUDE.md — RPDR Tracking

Operating guide for Claude Code (and any contributor). Read this first.

## What this is

A relational database of **RuPaul's Drag Race** (US main series, Seasons 1–18) and an
original, copyright-safe data-visualization website ("THE WERKROOM") built from it. The
ten CSV tables in `data/` are the **single source of truth**; everything else is generated
from them. Future phases: All Stars, then the international franchises.

## Golden rules (do not break these)

1. **Never invent data.** If a value is unknown, use `-` and flag it for verification. A
   blank is always better than a guess.
2. **`data/*.csv` is the source of truth.** Don't hand-edit generated files
   (`site/site_data.js`, `dist/DragRaceDB_master.xlsx`, `site/index.embedded.html`).
3. **Preserve the schema and IDs exactly.** Don't rename columns or reuse IDs. A performer
   keeps one `queen_id` across every season.
4. **`episodes.eliminated_id` is ground truth** for who went home; a standard NORMAL
   no-save lip-sync loser must reconcile to it. The `contestants` win/high/low/bottom
   tallies and `songs.times_used` are **computed**, never hand-typed.
5. **Cite sources for new data.** Prefer the season's Wikipedia page and individual episode
   pages; Fandom pages and Paramount+ synopses as secondary. The fetchable Wikipedia URL
   form uses `%27` (e.g. `.../RuPaul%27s_Drag_Race_season_5`), not the apostrophe form.
   **Do not use browser automation** — source via read-only fetch/search only.
6. **Original visual identity only.** No official logos, trade dress, photographs, or
   social-media handles. Names and outbound links are fine.
7. **One season at a time**, verified end-to-end, with the change set surfaced for review
   before moving on.

## How the project fits together

```
data/*.csv ──build_site_data.py──▶ site/site_data.js  ◀── loaded by ── site/index.html
        ├──build_xlsx.py──▶ dist/DragRaceDB_master.xlsx           (all views; edit this)
        └──validate.py  (must pass before committing)
```

- `site/index.html` — the website: HTML/CSS + 31 view functions. **Edit this for views.**
  It loads its data via `<script src="site_data.js">`, which defines a global `DATA`.
- `site/site_data.js` — generated data (a `var DATA = {…}` assignment). Regenerate it;
  never edit by hand.
- `site/index.embedded.html` — a frozen self-contained snapshot (data baked in) kept as an
  offline fallback. Not part of the live build.

## Commands

```bash
python scripts/validate.py            # data-integrity gate — run after ANY data edit
python scripts/build_site_data.py     # data/*.csv -> site/site_data.js  (after data edits)
python scripts/build_xlsx.py          # data/*.csv -> dist/DragRaceDB_master.xlsx
cd site && python3 -m http.server     # local preview at http://localhost:8000
```

Typical loop after editing a CSV: **validate → build_site_data → (commit).** Editing views
means editing `site/index.html` only; it never requires regenerating data.

## Working style (the owner, Bryan)

- Writes in ALL CAPS; prefers **phased, reviewable progress with checkpoints** over silent
  end-to-end runs. Surface a plan and pause at natural decision points.
- Favors **targeted edits over wholesale rewrites**; stays in control of the final voice.
- Will upload Fandom PDFs to provide richer detail when a Wikipedia source is thin.

## More detail

- `docs/DATA_MODEL.md` — full schema + every derived table (incl. the assassin-board math).
- `docs/CONVENTIONS.md` — vocabularies and the standing judgment calls.
- `docs/HANDOFF.md` — current state and the roadmap (S5–S18 verification next).
