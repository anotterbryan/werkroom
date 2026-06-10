# Data Model

The source of truth is the ten CSV tables in [`data/`](../data). Everything else —
`site/site_data.js`, `dist/DragRaceDB_master.xlsx`, and the data the site loads — is
**generated** from them. Never hand-edit a generated file; edit the CSVs and rebuild.

Scope: **RuPaul's Drag Race US main series (Seasons 1–18) + All Stars (in progress).**
Franchise is a first-class dimension via `seasons.franchise`, with extensible season-ID
prefixes — `US` (US main), `AS` (All Stars), reserved `UK` (Drag Race UK) and `CA`
(Canada's Drag Race) for the next imports. A performer keeps **one `queen_id` across every
franchise**, so cross-franchise links (e.g. a UK winner appearing on All Stars) resolve
automatically. The site reads the franchise list dynamically, so new franchises need no
view changes.

## Conventions in force

- Unknown / not-applicable values are `-` (never guessed). See [CONVENTIONS.md](CONVENTIONS.md).
- Dates are `YYYY-MM-DD`.
- A performer appears **once** in `queens`; each season they competed in is a row in
  `contestants` (queen-as-hub, appearances-as-spokes). Returning queens keep one `queen_id`.
- `contestants` win/high/low/bottom tallies and `songs.times_used` are **derived**, not
  hand-typed — `validate.py` recomputes and checks them.

## ID formats

| Entity | Format | Example |
|---|---|---|
| queen | `Q####` | `Q0001` |
| season | franchise + number | `US01` |
| episode | season + `E` + 2 digits | `US01E03` |
| contestant | season + `-` + queen | `US03-Q0007` |
| song | `S####` | `S0001` |
| progression | `P####` | `P0001` |
| lip sync | `L####` | `L0205` |
| elimination event | `E####` | `E0001` |
| panel | `PN####` | `PN0001` |
| appearance | `AP####` | `AP0001` |

---

## Tables

### queens — one row per performer
`queen_id` (PK), `drag_name`, `legal_name`, `birthdate`, `hometown`, `notes`

### seasons — one row per season
`season_id` (PK), `franchise`, `season_label`, `platform`, `host`, `premiere_date`,
`episode_count`, `winner_id`→queens, `miss_congeniality_id`→queens, `power_up_system`,
`cash_prize`
- `cash_prize` = the winner's headline grand prize in USD (integer, no separators;
  `-` if unverified). Sourced from the season's Fandom/Wikipedia finale. Cast to int by
  `build_site_data.py` (`INT_FIELDS["seasons"]`).

### contestants — one row per queen per season
`contestant_id` (PK), `queen_id`→queens, `season_id`→seasons, `placement`,
`entrance_order`, `home_city`, `wins`, `highs`, `lows`, `bottoms`,
`eliminated_episode`, `miss_congeniality`, `drag_name_used`
- `drag_name_used` = the name the performer competed under that season when it differs
  from her canonical `queens.drag_name` (e.g. Trinity Taylor → "Trinity The Tuck" in All
  Stars); `-` when the same. The `queen_id` is unchanged, so one identity spans every
  franchise. The site shows `drag_name_used` in season context, canonical name elsewhere.
- `home_city` = where the queen was based at the time of that season (may differ from
  `queens.hometown`, the canonical origin).
- `wins/highs/lows/bottoms` are **computed** from `progression` (see validate rule below).
- `placement`: 1 = winner, 2 = runner-up, etc. (official final placement).

### episodes — one row per episode
`episode_id` (PK), `season_id`→seasons, `episode_number`, `title`, `air_date`,
`main_challenge`, `main_challenge_type`, `mini_challenge`, `runway_theme`,
`lip_sync_song_id`→songs, `lip_sync_track`, `eliminated_id`→queens, `power_up_used`
- `eliminated_id` is the **ground truth** for who went home that episode (the
  `lip_syncs` loser must reconcile to it; see validate rule).
- `main_challenge_type` controlled vocabulary: Acting, Design, Girl Group, Makeover,
  Snatch Game, Comedy, Singing, Song-Verse, Talent Show, Finale, Reunion, Clip Show.

### progression — one row per queen per episode
`progression_id` (PK), `contestant_id`→contestants, `queen_id`→queens,
`season_id`→seasons, `episode_id`→episodes, `status`
- `status` vocabulary: `WIN`, `HIGH`, `SAFE`, `LOW`, `BTM`, `ELIM`, `WINNER`,
  `RUNNER-UP`, `RTRN`, `GUEST`, `SURVIVAL`/`STAY`, `IMM`, `WDR`, `DISQ`, etc.
- This grid is the basis for the `contestants` tallies.

### songs — one row per distinct lip-sync track
`song_id` (PK), `title`, `artist`, `times_used` (derived = distinct episodes the song
appears in, across `episodes` ∪ `lip_syncs`).

### lip_syncs — one row per lip sync performed
`lip_sync_id` (PK), `episode_id`→episodes, `song_id`→songs, `queen_a_id`→queens,
`queen_b_id`→queens, `winner_id`→queens, `loser_id`→queens, `result_type`, `was_save`,
`notes`
- `result_type`: `NORMAL` (loser eliminated), `SURVIVAL` (winner stays, no elimination —
  counts as a win), `SHANTAY` (double save; blank winner/loser), `SASHAY` (double
  elimination; blank winner/loser), `TOPS` (lip sync for the win, top-2 format, no
  elimination), `CROWN` (finale lip sync for the crown).

### elimination_events — one row per elimination-type event
`event_id` (PK), `queen_id`→queens, `season_id`→seasons, `episode_id`→episodes,
`event_type`, `decided_by_queen_id`→queens, `notes`
- `event_type`: eliminated, returned, withdrew, disqualified, saved-no-elimination, reversed.
- A returnee (e.g. a queen eliminated then brought back) has multiple rows here.

### panel — one row per judge/host credit per season
`panel_id` (PK), `person_name`, `season_id`→seasons, `role` (HOST, MAIN_JUDGE, …)

### appearances — one row per guest credit
`appearance_id` (PK), `person_name`, `season_id`→seasons, `episode_id`→episodes,
`appearance_type` (GUEST_JUDGE, MAINSTAGE_GUEST, WERKROOM_GUEST), `role_detail`,
`is_drag_race_alum`, `alum_queen_id`→queens, `notes`

---

## Derived block (`site_data.js` → the global `DATA.derived`)

`build_site_data.py` computes 12 structures. The seven that depend only on
unchanged source tables are validated byte-for-byte against the prior build.

| key | shape | derivation |
|---|---|---|
| `returning_queens` | list | queens in >1 season; `{queen_id, drag_name, seasons[]}`, sorted by name |
| `song_reuse` | list | every song + sorted distinct episodes used in; `times_used = len(episodes)` |
| `assassin_board` | list | per-queen lip-sync record (see below) |
| `guest_freq` | list | count of `GUEST_JUDGE` rows per person (incl. season-level credits with no episode); `episodes` = sorted named episodes; sort `(-count, first-appearance)` |
| `panel_by_season` | obj | `{season_id: [{name, role}, …]}` |
| `alumni_links` | list | appearances where `is_drag_race_alum == "Yes"` |
| `tally` | list | `contestants` joined with `drag_name` |
| `hometowns` | obj→list | frequency of `queens.hometown`; sort `(-count, first-appearance)` |
| `challenge_types` | obj | `Counter(main_challenge_type)`, sorted `(-count, name)` |
| `snatch_index` | list | episodes whose type is `Snatch Game` or title contains it |
| `qname` | obj | `{queen_id: drag_name}` |
| `slabel` | obj | `{season_id: season_label}` |

### assassin_board derivation (exact)

Members = every `winner_id` of any lip sync **plus** both participants of every
`SHANTAY` / `SASHAY` row (those rows have blank winner/loser). For each member:

- `by_type[t]` — for `NORMAL/SURVIVAL/TOPS/CROWN`, count of rows the queen **won**;
  for `SHANTAY/SASHAY`, count of rows the queen **participated** in.
- `ls_wins` = `NORMAL + SURVIVAL + SHANTAY + TOPS + CROWN` (a SASHAY is a double
  elimination, so it is tracked but **not** counted as a win).
- `assassinations` = `NORMAL` wins **plus** `CROWN` wins where `was_save == "No"` and a
  `loser_id` is set (i.e. lip syncs that actually sent someone home / clinched the crown
  head-to-head).
- `shantays` = `SHANTAY` participations; `sashays` = `SASHAY` participations.
- Sort: `(-ls_wins, -assassinations, drag_name)`.

---

## Validated invariants (`scripts/validate.py`)

1. Primary keys unique and present; foreign keys resolve.
2. **Ground truth** — for an episode with a single `NORMAL`/no-save lip sync, the
   `loser_id` equals `episodes.eliminated_id`.
3. **Tally formula** — `wins = #WIN`, `highs = #HIGH`, `lows = #LOW`,
   `bottoms = #BTM + #ELIM` from `progression`, for every contestant.
4. `songs.times_used` = distinct episodes the song appears in.

All 31 checks currently pass.
