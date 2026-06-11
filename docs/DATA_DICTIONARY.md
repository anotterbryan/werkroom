# Werkroom Data Dictionary

_The master spec: every dimension fans obsess over, mapped to where it lives (or should live)
in the CSV relational model, what the site uses it for, where the truth comes from, and how
complete it is. Drafted 2026-06-10 against the live data (48 seasons · 7 franchises ·
409 queens · 532 episodes · 498 songs). Spec-first: this document gates what we clip and
import next._

**How to read the tables**

- **Maps to** — `table.column` in `data/*.csv`, the source of truth. *(derived)* = computed
  by `build_site_data.py`, never stored. *(to add)* = proposed, see §8.
- **Filter / view use** — the site views (by `id`) that consume or would consume it.
- **Source** — the authoritative document we extract from: `WP-MD` (Wikipedia markdown clips,
  `Fandom/RPDR MD/`), `Fandom` (Fandom HTML, per-franchise folders), `IMDb` (not yet clipped),
  `Spotify` (MCP, paused — enrichment only).
- **Status** — ✅ have (≥95% where applicable) · 🟡 partial (with measured coverage) ·
  ⬜ to-add (schema and/or data missing). Coverage figures measured 2026-06-10.

Franchise key: US = US main (18 seasons), AS = All Stars (11), UK (7), CA (6), UW = UK vs the
World (3), CW = Canada vs the World (2), GA = Global All Stars (1).

---

## 1. Queens — identity & biography

| Dimension | Maps to | Filter / view use | Source | Status |
|---|---|---|---|---|
| Drag name (canonical) | `queens.drag_name` | everywhere (`qname` lookup) | WP-MD / Fandom | ✅ 409/409 |
| Name competed under | `contestants.drag_name_used` | season context (`season`, `queen`) | WP-MD / Fandom | ✅ by design — filled only when it differs (15 rows) |
| Legal name | `queens.legal_name` | `queen` profile | WP-MD (Contestants table / article lead) | 🟡 178/409 (43%) |
| Birthdate | `queens.birthdate` | `queen` profile; age math | WP-MD / Fandom | 🟡 180/409 (44%) |
| Zodiac sign | *(derived from birthdate)* | `queen` profile; a future zodiac view | derivation | ⬜ blocked by birthdate coverage |
| Hometown (origin) | `queens.hometown` | `hometowns` geography | WP-MD / Fandom | 🟡 282/409 (69%) |
| City represented that season | `contestants.home_city` | `season` detail; geography by season | WP-MD Contestants table ("hometown" col) | ⬜ 47/571 (8%) — US-only so far |
| Age at filming | `contestants.age_at_filming` *(to add)* | `season` cast list; youngest/oldest records | WP-MD Contestants table ("Age" col) | ⬜ column missing; source has it for all 18 US seasons |
| Drag family (mother/daughter) | `queens.drag_mother_id` *(to add)* or `drag_family` table *(to add)* | family-tree view (planned) | Fandom (trivia/bio) — curated | ⬜ |
| Socials (IG/X/etc.) | `queens.socials` *(to add)* | `queen` profile links | Fandom infobox | ⬜ |
| Image / photo | `queens.image` *(to add — URL or repo path)* | `queens` grid, `queen` profile | Fandom (promo looks) | ⬜ licensing question open |
| Notes / trivia | `queens.notes` | `queen` profile | curated | 🟡 171/409 free-text |

## 2. Per-episode performance

| Dimension | Maps to | Filter / view use | Source | Status |
|---|---|---|---|---|
| Status grid (WIN/HIGH/SAFE/LOW/BTM/ELIM…) | `progression.status` | `placementgrid`, `season`, `perfectrun`, tallies | WP-MD Contestant progress grid | ✅ 4208 rows, all 48 seasons |
| Win/high/low/bottom tallies | `contestants.wins/highs/lows/bottoms` *(derived from progression; validated)* | `tallies`, `winscatter`, `queen` | derivation | ✅ validated by rule 4 |
| Final placement | `contestants.placement` | `placementgrid`, `tallies`, `winners` | WP-MD Contestants table | ✅ 570/571 |
| Entrance order | `contestants.entrance_order` | `entrance` (Entrance Order & Fate) | Fandom (episode 1 recaps) | 🟡 157/242 US; 0 elsewhere |
| Lip-sync song that episode | `episodes.lip_sync_song_id` (+ `lip_sync_track` text) | `songreuse`, `artists`, `episodes` | WP-MD Lip syncs table | 🟡 481/532 (90%) — gaps are finales/reunions with no lip sync |
| Lip-sync opponent + result (head-to-head) | `lip_syncs.*` (queens a/b, winner, loser, `result_type`, `was_save`) | `assassin` board | WP-MD Lip syncs table | 🟡 US-only (270 rows). AS/CA/UK/UW/CW/GA have song-at-episode but **no head-to-head rows** |
| "Assassin" stats | *(derived: `assassin_board`)* | `assassin` | derivation | ✅ for US; blank elsewhere until head-to-head rows exist |
| Eliminated that episode | `episodes.eliminated_id` (ground truth) + `elimination_events` | `elimorder`, validation rule 2 | WP-MD progress grid / Lip syncs | ✅ where an elimination occurred (383/532; rest are no-elim episodes) |
| Snatch Game character | `snatch_characters` table *(to add: contestant_id, episode_id, character)* | `snatch` index (today: episodes only) | Fandom episode pages | ⬜ |
| Makeover partner | `episode_roles` *(to add)* | makeover view (planned) | Fandom episode pages | ⬜ |
| Rusical / acting role | `episode_roles` *(to add: contestant, episode, role_type, role)* | challenge-detail views | Fandom episode pages | ⬜ |
| Runway theme | `episodes.runway_theme` | `episodes` browser; runway view (planned) | WP-MD episode prose / Fandom | 🟡 400/532 (75%) |
| Runway look (description/image) | `looks` table *(to add: contestant, episode, category, description, image)* | runway gallery (planned) | Fandom (richest source) | ⬜ |

## 3. Episodes

| Dimension | Maps to | Filter / view use | Source | Status |
|---|---|---|---|---|
| Title | `episodes.title` | `episodes`, `snatch` | WP-MD Episodes table | ✅ 530/532 |
| Number in season | `episodes.episode_number` | ordering everywhere | WP-MD | ✅ |
| Number overall (franchise-wide) | *(derive from season order + episode_number)* | `episodes` browser | WP-MD has "No. overall" | ⬜ derive, don't store |
| Air date | `episodes.air_date` | air-date table (planned), cadence views | WP-MD Episodes table | ✅ 531/532 — **already filled**; task #41 becomes *verify* vs WP-MD, not harvest |
| Episode type | `episodes.main_challenge_type` (controlled vocab incl. Finale, Reunion) | `challenges`, `snatch` | WP-MD / Fandom | ✅ 531/532 |
| Main challenge | `episodes.main_challenge` | `episodes`, `challenges` | WP-MD prose / Fandom | 🟡 500/532 (94%) |
| Mini challenge | `episodes.mini_challenge` | `episodes` detail | Fandom (WP rarely has it) | 🟡 280/532 (53%) |
| Guest judges (per episode) | `appearances` (`GUEST_JUDGE`) | `guestfreq`, `guestdir` | WP-MD Guest judges bullets (episode numbers included) | 🟡 245 rows, **US-only**; 0 for AS/UK/CA/UW/CW/GA |
| Special guests | `appearances` (`MAINSTAGE_GUEST`, `WERKROOM_GUEST`) | `apptypes`, `alumniweb` | WP-MD Special guests (S5+; none existed S1–4) | 🟡 150 rows, US-only |
| Guest "known for" blurb | `guests.csv known_for` (11th table, optional) | `guestdir` hover bios | curated | 🟡 19 people |
| Ratings / viewers | `episodes.imdb_rating`, `viewers` *(to add)* | ratings views (planned) | IMDb (not yet clipped) | ⬜ |
| Director | `episodes.director` *(to add)* | trivia | IMDb | ⬜ |

## 4. Seasons

| Dimension | Maps to | Filter / view use | Source | Status |
|---|---|---|---|---|
| Franchise | `seasons.franchise` | `FRANCHISE` side-filters, `atlas` | — | ✅ 48/48 |
| Premiere date | `seasons.premiere_date` | `atlas`, `platforms` timeline | WP-MD | ✅ 48/48 |
| Finale date | `seasons.finale_date` *(to add — or derive from max air_date)* | season span views | WP-MD Episodes table | ⬜ derivable today from `episodes.air_date` |
| Episode count | `seasons.episode_count` | `atlas`, `seasonsize` | WP-MD | ✅ 48/48 |
| Winner / runners-up | `seasons.winner_id`; runners-up via `contestants.placement` | `winners` | WP-MD | ✅ 47/48 (1 season in progress) |
| Miss Congeniality | `seasons.miss_congeniality_id` + `contestants.miss_congeniality` | `missc` | WP-MD / Fandom | 🟡 17/18 US; **0 for all other franchises** |
| Cash prize (+ currency) | `seasons.cash_prize` (USD int); `cash_prize_currency` *(to add)* | `atlas`, `winners` | WP-MD finale coverage | 🟡 28/48 — US 18/18, AS 10/11, **0 intl** (currency blocker: UK has no cash prize at all; CA/intl pay CAD etc.) |
| Host & judging panel | `seasons.host`; `panel` (HOST, MAIN_JUDGE…) | `panel`, `tenure` | WP-MD / Fandom | host ✅ 48/48; panel 🟡 74 rows **US-only** |
| Format / twists | `seasons.power_up_system` + `episodes.power_up_used` | `season` detail | WP-MD / Fandom | ⬜ both columns exist but are **0% filled** — define vocab or drop |
| Filming location | `seasons.filming_location` *(to add)* | trivia, `atlas` | WP-MD / Fandom | ⬜ |
| Platform / network | `seasons.platform` | `platforms` eras | WP-MD | ✅ 48/48 |

## 5. Songs & music

| Dimension | Maps to | Filter / view use | Source | Status |
|---|---|---|---|---|
| Lip-sync song (title/artist) | `songs.title`, `songs.artist` | `songreuse`, `artists` | **WP-MD Lip syncs table** (verification source of record) | ✅ 497/498 — `S0285` (US18 E12/E13) blank, fix queued in task #40 |
| Song reuse across episodes | `songs.times_used` *(derived; validated)* + `derived.song_reuse` | `songreuse` | derivation | ✅ |
| RuPaul originals / Ru-mixes | `songs.is_rumix` *(to add — auto-taggable when artist == RuPaul)* | playlist filters, Ru-mix view | WP-MD + curation (~20 known) | ⬜ |
| Original challenge songs (girl-group / Rusical / verses) | `challenge_songs` *(to add)* or rows in `songs` + `episode_roles` link | music views (planned) | Fandom / WP-MD | ⬜ task #39 |
| Spotify track ID | `songs.spotify_track_id` | play embeds, playlists (tasks #34–38) | Spotify MCP (paused) | ⬜ column added (uncommitted), 0/498 matched |
| Artist name normalization | `songs.artist` | clean `artists` rollup | WP-MD reconciliation | 🟡 11 cosmetic + 14 real corrections + 25 missing songs queued (task #40 — reconciliation report must be regenerated, prior copy lost with session outputs) |

## 6. Records & superlatives (all derived — never stored)

| Dimension | Derivation basis | View | Status |
|---|---|---|---|
| Most challenge wins / best track record | `progression` → `tally` | `tallies`, `winscatter` | ✅ |
| Most lip-syncs won / assassins | `lip_syncs` → `assassin_board` | `assassin` | ✅ US; intl blocked on head-to-head rows |
| Perfect runs (never below SAFE) | `progression` | `perfectrun` | ✅ |
| Immunity runs | `progression.status` = `IMM` | future view | ✅ data exists in vocab |
| Lowest placement to win / comeback stats | `progression` + `placement` | future view | ✅ derivable |
| Returnees & cross-franchise runs | `contestants` per queen → `returning_queens` | `returning`, `connect` | ✅ |
| Disqualifications / withdrawals | `elimination_events.event_type`, `progression` `DISQ`/`WDR` | `elimorder` | ✅ |
| Double shantay / double sashay | `lip_syncs.result_type` `SHANTAY`/`SASHAY` | `assassin` | ✅ US-only (same gap) |
| Guest-judge frequency | `appearances` → `guest_freq` | `guestfreq` | ✅ US-only |
| Drag-family trees | *(to add — needs §1 family fields)* | planned | ⬜ |
| Oldest/youngest at filming | *(to add — needs `age_at_filming`)* | planned | ⬜ |

---

## 7. Cross-cutting gaps (the real backlog, measured)

1. **International depth.** The non-US franchises have the skeleton (seasons, contestants,
   placements, progression, episodes, songs) but are missing nearly all texture: panel (0 rows),
   guest judges (0), special guests (0), Miss Congeniality (0), cash prize (0), entrance order (0),
   lip-sync head-to-head (0). Every one of these is harvestable from the same two sources once
   their pages are clipped to MD.
2. **Lip-sync head-to-head outside US** — blocks `assassin`/shantay/sashay stats for 30 seasons.
3. **Queens biography** — legal name 43%, birthdate 44%, hometown 69%; `home_city` 8%.
4. **Dead columns** — `seasons.power_up_system` and `episodes.power_up_used` are 0% filled.
   Decide: define a controlled vocabulary and backfill, or drop both.
5. **`guests.csv`** is a real 11th table (person_name, known_for) consumed by
   `build_site_data.py` but absent from `DATA_MODEL.md` — document it there.

## 8. Proposed schema additions

New columns (additive, default `-`, no migration risk):

| Table | Column | Notes |
|---|---|---|
| `queens` | `drag_mother_id` | FK → queens; `-` when unknown. Trees derive from this single edge. |
| `queens` | `socials` | pipe-separated `platform:handle` pairs, or split later |
| `queens` | `image` | URL or `site/img/` path; settle licensing first |
| `contestants` | `age_at_filming` | int; from WP-MD Contestants table |
| `episodes` | `imdb_rating`, `imdb_votes`, `viewers_m`, `director` | IMDb harvest; floats/ints, `-` default |
| `seasons` | `finale_date` | or derive = max(air_date); storing keeps seasons self-contained |
| `seasons` | `cash_prize_currency` | ISO code; `cash_prize` becomes native-currency int |
| `seasons` | `filming_location` | city, country |
| `songs` | `is_rumix` | Yes/No; auto-tag artist == RuPaul + curated list |

New tables (only where a dimension is one-to-many per contestant-episode):

| Table | Key columns | Powers |
|---|---|---|
| `episode_roles` | `role_id`, `contestant_id`, `episode_id`, `role_type` (SNATCH_CHARACTER, MAKEOVER_PARTNER, RUSICAL_ROLE, ACTING_ROLE, GIRL_GROUP_VERSE), `role_detail` | Snatch Game characters, makeover partners, Rusical/acting roles, verse credits — one mechanism for all |
| `looks` | `look_id`, `contestant_id`, `episode_id`, `category` (RUNWAY, PROMO, ENTRANCE), `description`, `image` | runway galleries; biggest Fandom payoff |

Sequencing: add columns + `episode_roles` first (cheap, validate.py grows FK checks);
`looks` last (images/licensing). Every addition ships with its validate.py check.

## 9. Per-season clipping checklist

For each season not yet covered by a Wikipedia MD clip (everything except US S1–18), clip to
`Fandom/<source folder>/` with frontmatter `source_type`, `franchise`, `season_id` (e.g. `UK03`):

**Wikipedia MD (primary)** — verify the clip contains:
- [ ] `## Contestants` table (name, age, hometown, outcome) → contestants + `age_at_filming`
- [ ] `## Contestant progress` grid → progression
- [ ] `## Lip syncs` table → lip_syncs head-to-head + songs
- [ ] `## Guest judges` bullets (with episode numbers) → appearances
- [ ] `### Special guests` (may not exist for early seasons) → appearances
- [ ] `## Episodes` table (no./title/air date) → air-date verification, finale_date
- [ ] Infobox/lead: host, panel, platform, prize (+currency), filming location

**Fandom HTML (supplement, already saved for all 48 seasons)** — extract on demand:
entrance order, mini-challenge winners, Snatch Game characters, makeover pairs, runway/look
detail + images, trivia.

**IMDb (deferred, decided 2026-06-10)** — when wanted: one MD clip per season from the
per-season episode list page → `Fandom/IMDb MD/`, filling `imdb_rating`/`viewers_m`/`director`.

## 10. Source folder map (as-is, decided to keep)

| Folder (`…/Werkroom/Fandom/`) | Source | Coverage |
|---|---|---|
| `RPDR MD/` | Wikipedia markdown | US S1–18 + main article ✅ |
| `RPDR Wiki/` | Wikipedia HTML (backup) | US S1–18 + episodes list |
| `RuPaul's Drag Race/` | Fandom HTML | US S1–19 |
| `RuPaul's Drag Race All Stars/` | Fandom HTML | AS S1–12 |
| `RuPaul's Drag Race UK/` | Fandom HTML | UK S1–7 |
| `Canada's Drag Race/` | Fandom HTML | CA S1–7 |
| `RuPaul's Drag Race UK vs The World/` | Fandom HTML | UW S1–3 |
| `Canada vs The World/` | Fandom HTML | CW S1–2 |
| `Global All Stars/` | Fandom HTML | GA S1 |
| `Rupaul's Drag Race Untucked/` | Fandom HTML | S1–17 (not in DB; no current table) |

Wikipedia MD clips for the international franchises do not exist yet — they are the
prerequisite for closing every gap in §7.
