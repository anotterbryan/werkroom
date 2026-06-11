#!/usr/bin/env python3
"""
build_site_data.py  --  Compile the CSV source-of-truth in data/ into site/site_data.js.

site_data.js is the single data artifact the website (site/index.html) loads via
<script src="site_data.js">. It assigns one global `DATA` object containing:
  * the 10 relational tables, lightly typed (counts -> int, blanks -> null where appropriate)
  * a `meta` block of row counts
  * a `derived` block of 12 pre-computed tables/lookups used by the views

The data/*.csv files are the only source of truth. This script is pure and deterministic:
running it again on the same CSVs produces byte-identical output. Because the data lives in
its own file, rebuilding it never modifies index.html or your view code.

Usage:
    python scripts/build_site_data.py            # writes site/site_data.js
    python scripts/build_site_data.py --check     # build in memory, print summary, write nothing
"""
import csv, json, sys, argparse, datetime
from pathlib import Path
from collections import Counter, defaultdict, OrderedDict

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
# The site loads its data from this file via <script src="site_data.js">. It assigns
# a single global `DATA` object (the JSON below), which index.html then reads. Keeping
# the data in its own file means a data rebuild never touches index.html / your views.
OUT = ROOT / "site" / "site_data.js"

BLANKS = ("", "-")  # values treated as "no data"

TABLES = ["queens", "seasons", "contestants", "episodes", "progression",
          "songs", "lip_syncs", "elimination_events", "panel", "appearances",
          "episode_roles"]

# Per-table fields cast to int (None when blank). Everything else stays a string,
# matching the historical site_data.json typing exactly.
INT_FIELDS = {
    "contestants": {"placement", "entrance_order", "wins", "highs", "lows", "bottoms",
                    "earnings"},
    "seasons": {"cash_prize"},
}
LS_WIN_TYPES = ["NORMAL", "SURVIVAL", "SHANTAY", "TOPS", "CROWN", "SASHAY"]


def read_csv(name):
    with open(DATA / f"{name}.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def cast_rows(name, rows):
    """Apply the int/null casting rules; leave all other fields as strings."""
    intf = INT_FIELDS.get(name, set())
    out = []
    for r in rows:
        rec = OrderedDict()
        for k, v in r.items():
            if k in intf:
                rec[k] = int(v) if str(v).strip() not in BLANKS else None
            else:
                rec[k] = v
        out.append(rec)
    return out


def build():
    raw = {t: read_csv(t) for t in TABLES}
    data = OrderedDict()

    # ---- meta -------------------------------------------------------------
    data["meta"] = OrderedDict([
        ("generated", datetime.date.today().isoformat()),
        ("seasons", len(raw["seasons"])),
        ("queens", len(raw["queens"])),
        ("contestants", len(raw["contestants"])),
        ("episodes", len(raw["episodes"])),
        ("appearances", len(raw["appearances"])),
        ("songs", len(raw["songs"])),
    ])

    # ---- core tables ------------------------------------------------------
    for t in TABLES:
        data[t] = cast_rows(t, raw[t])

    # ---- derived ----------------------------------------------------------
    data["derived"] = build_derived(raw)
    return data


def build_derived(raw):
    queens, seasons = raw["queens"], raw["seasons"]
    contestants, episodes = raw["contestants"], raw["episodes"]
    songs, lip_syncs = raw["songs"], raw["lip_syncs"]
    panel, appearances = raw["panel"], raw["appearances"]

    qname = {q["queen_id"]: q["drag_name"] for q in queens}
    slabel = {s["season_id"]: s["season_label"] for s in seasons}

    d = OrderedDict()

    # returning_queens: queens with >1 season (in contestant order of seasons)
    seasons_by_q = defaultdict(list)
    for c in contestants:
        if c["season_id"] not in seasons_by_q[c["queen_id"]]:
            seasons_by_q[c["queen_id"]].append(c["season_id"])
    returning = [{"queen_id": q, "drag_name": qname.get(q), "seasons": s}
                 for q, s in seasons_by_q.items() if len(s) > 1]
    returning.sort(key=lambda x: (x["drag_name"] or ""))
    d["returning_queens"] = returning

    # song_reuse: every song + the distinct episodes it was lip-synced in
    song_eps = defaultdict(set)
    for e in episodes:
        sid = e["lip_sync_song_id"]
        if sid not in BLANKS:
            song_eps[sid].add(e["episode_id"])
    for r in lip_syncs:
        if r["song_id"] not in BLANKS:
            song_eps[r["song_id"]].add(r["episode_id"])
    d["song_reuse"] = [
        {"song_id": s["song_id"], "title": s["title"], "artist": s["artist"],
         "times_used": len(song_eps.get(s["song_id"], set())),
         "episodes": sorted(song_eps.get(s["song_id"], set()))}
        for s in songs
    ]

    # assassin_board: per-queen lip-sync record (see derivation notes in docs/DATA_MODEL.md)
    bt = defaultdict(Counter)
    members = set()
    crown_kill = Counter()
    for r in lip_syncs:
        t = r["result_type"]
        if t in ("SHANTAY", "SASHAY"):
            for qid in (r["queen_a_id"], r["queen_b_id"]):
                if qid not in BLANKS:
                    bt[qid][t] += 1
                    members.add(qid)
        else:
            w = r["winner_id"]
            if w not in BLANKS:
                bt[w][t] += 1
                members.add(w)
                if t == "CROWN" and r["was_save"] == "No" and r["loser_id"] not in BLANKS:
                    crown_kill[w] += 1
    board = []
    for qid in members:
        c = bt[qid]
        board.append({
            "queen_id": qid, "drag_name": qname.get(qid),
            "ls_wins": c["NORMAL"] + c["SURVIVAL"] + c["SHANTAY"] + c["TOPS"] + c["CROWN"],
            "assassinations": c["NORMAL"] + crown_kill[qid],
            "shantays": c["SHANTAY"], "sashays": c["SASHAY"],
            "by_type": {t: c[t] for t in LS_WIN_TYPES},
        })
    board.sort(key=lambda x: (-x["ls_wins"], -x["assassinations"], x["drag_name"] or ""))
    d["assassin_board"] = board

    # guest_freq: number of GUEST JUDGE credits per person (rows, including
    # season-level credits with no specific episode); episodes lists the named ones
    gj = defaultdict(list)
    gj_first = {}
    for i, a in enumerate(appearances):
        if a["appearance_type"] == "GUEST_JUDGE":
            gj[a["person_name"]].append(a["episode_id"])
            gj_first.setdefault(a["person_name"], i)
    gf = [{"name": n, "appearances": len(eids),
           "episodes": sorted({e for e in eids if e not in BLANKS})}
          for n, eids in gj.items()]
    gf.sort(key=lambda x: (-x["appearances"], gj_first[x["name"]]))
    d["guest_freq"] = gf

    # panel_by_season
    pbs = OrderedDict()
    for s in seasons:
        pbs[s["season_id"]] = [
            {"name": p["person_name"], "role": p["role"]}
            for p in panel if p["season_id"] == s["season_id"]
        ]
    d["panel_by_season"] = pbs

    # alumni_links: appearances by Drag Race alumni
    d["alumni_links"] = [
        {"person": a["person_name"], "queen_id": a["alum_queen_id"],
         "season": a["season_id"], "episode": a["episode_id"], "type": a["appearance_type"]}
        for a in appearances if a["is_drag_race_alum"] == "Yes"
    ]

    # tally: contestant scorecard joined with drag name
    def as_int(v):
        return int(v) if str(v).strip() not in BLANKS else None
    d["tally"] = [
        {"queen_id": c["queen_id"], "drag_name": qname.get(c["queen_id"]),
         "season": c["season_id"], "placement": as_int(c["placement"]),
         "wins": as_int(c["wins"]), "highs": as_int(c["highs"]),
         "lows": as_int(c["lows"]), "bottoms": as_int(c["bottoms"]),
         "miss_c": c["miss_congeniality"]}
        for c in contestants
    ]

    # hometowns: frequency of canonical hometown (ties broken by first appearance)
    ht = Counter()
    first_seen = {}
    for i, q in enumerate(queens):
        h = q["hometown"]
        if h not in BLANKS:
            ht[h] += 1
            first_seen.setdefault(h, i)
    d["hometowns"] = [{"hometown": h, "count": n} for h, n in
                      sorted(ht.items(), key=lambda kv: (-kv[1], first_seen[kv[0]]))]

    # challenge_types: frequency of main_challenge_type
    ct = Counter(e["main_challenge_type"] for e in episodes
                 if e["main_challenge_type"] not in BLANKS)
    d["challenge_types"] = OrderedDict(sorted(ct.items(), key=lambda kv: (-kv[1], kv[0])))

    # snatch_index: every Snatch Game episode
    d["snatch_index"] = [
        {"episode_id": e["episode_id"], "season": e["season_id"], "title": e["title"]}
        for e in episodes if e["main_challenge_type"] == "Snatch Game"
        or "Snatch Game" in e["title"]
    ]

    # guest_bios: optional one-line "known for" descriptors keyed by person_name
    guest_bios = {}
    gpath = DATA / "guests.csv"
    if gpath.exists():
        with open(gpath, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                kf = (r.get("known_for") or "").strip()
                if kf and kf not in BLANKS:
                    guest_bios[r["person_name"]] = kf
    d["guest_bios"] = guest_bios

    # lookups
    d["qname"] = qname
    d["slabel"] = slabel
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="build in memory, write nothing")
    args = ap.parse_args()

    data = build()
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    text = f"var DATA = {payload};\n"

    print(f"built site_data: {data['meta']['songs']} songs, "
          f"{len(data['derived']['assassin_board'])} on assassin board, "
          f"{len(payload):,} bytes of data")
    if args.check:
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
