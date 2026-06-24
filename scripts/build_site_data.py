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
          "episode_roles", "episode_moments"]

# Per-table fields cast to int (None when blank). Everything else stays a string,
# matching the historical site_data.json typing exactly.
INT_FIELDS = {
    "contestants": {"placement", "entrance_order", "wins", "highs", "lows", "bottoms",
                    "earnings", "age_at_filming"},
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

    # season_summary: a fully-computed per-season at-a-glance + superlatives block
    d["season_summary"] = build_season_summary(raw, qname)

    # season_narratives: editorial prose keyed by season_id, loaded from a CSV
    # (created with empty rows if absent, so a later stage can fill it in)
    d["season_narratives"] = build_season_narratives(seasons)

    # lookups
    d["qname"] = qname
    d["slabel"] = slabel
    return d


def _to_int(v):
    """Parse an int, returning None for blanks / non-numeric values."""
    try:
        s = str(v).strip()
        return int(s) if s not in BLANKS else None
    except (TypeError, ValueError):
        return None


def build_season_summary(raw, qname):
    """Compute a deterministic per-season summary dict keyed by season_id.

    Every field is derived from the source tables and degrades gracefully to
    null / "-" / empty list when the underlying data is missing.
    """
    seasons = raw["seasons"]
    contestants = raw["contestants"]
    episodes = raw["episodes"]
    progression = raw["progression"]
    lip_syncs = raw["lip_syncs"]
    songs = raw["songs"]
    elim_events = raw["elimination_events"]
    roles = raw["episode_roles"]
    appearances = raw["appearances"]

    song_title = {}
    for s in songs:
        t = (s.get("title") or "").strip()
        song_title[s["song_id"]] = t if t not in BLANKS else None

    # index helpers ---------------------------------------------------------
    cons_by_season = defaultdict(list)
    for c in contestants:
        cons_by_season[c["season_id"]].append(c)
    eps_by_season = defaultdict(list)
    for e in episodes:
        eps_by_season[e["season_id"]].append(e)
    ep_season = {e["episode_id"]: e["season_id"] for e in episodes}
    ls_by_season = defaultdict(list)
    for l in lip_syncs:
        sid = ep_season.get(l["episode_id"])
        if sid:
            ls_by_season[sid].append(l)
    elim_by_season = defaultdict(list)
    for ev in elim_events:
        elim_by_season[ev["season_id"]].append(ev)
    roles_by_season = defaultdict(list)
    con_season = {c["contestant_id"]: c["season_id"] for c in contestants}
    for r in roles:
        sid = con_season.get(r["contestant_id"])
        if sid:
            roles_by_season[sid].append(r)

    def name(qid):
        return qname.get(qid) if qid and qid not in BLANKS else None

    def cdisplay(c):
        used = (c.get("drag_name_used") or "").strip()
        if used and used not in BLANKS:
            return used
        return qname.get(c["queen_id"]) or c["queen_id"]

    out = OrderedDict()
    for s in seasons:
        sid = s["season_id"]
        cs = cons_by_season.get(sid, [])
        eps = eps_by_season.get(sid, [])
        lss = ls_by_season.get(sid, [])
        evs = elim_by_season.get(sid, [])

        # ranked cast by placement (unknown placement sinks to the bottom)
        def plc(c):
            p = _to_int(c.get("placement"))
            return p if p is not None else 999
        ranked = sorted(cs, key=plc)

        # winner ------------------------------------------------------------
        winner = name(s.get("winner_id"))
        if not winner:
            w1 = [c for c in cs if _to_int(c.get("placement")) == 1]
            winner = cdisplay(w1[0]) if w1 else None

        # runners-up (placement == 2, includes ties) ------------------------
        runners_up = [cdisplay(c) for c in cs if _to_int(c.get("placement")) == 2]

        # miss congeniality -------------------------------------------------
        mc = name(s.get("miss_congeniality_id"))
        if not mc:
            mcc = [c for c in cs if (c.get("miss_congeniality") or "") == "Yes"]
            mc = cdisplay(mcc[0]) if mcc else None

        # finale format (inferred from finale lip syncs) --------------------
        finale_format = None
        crown_ls = [l for l in lss if l["result_type"] == "CROWN"]
        top_placements = sorted({_to_int(c.get("placement")) for c in cs
                                 if _to_int(c.get("placement")) is not None
                                 and 1 <= (_to_int(c.get("placement")) or 0) <= 4})
        if crown_ls:
            n_crown = len(crown_ls)
            finale_format = ("Lip Sync for the Crown bracket" if n_crown > 1
                             else "Lip Sync for the Crown")
        elif 4 in top_placements:
            finale_format = "Top 4 finale"
        elif 3 in top_placements:
            finale_format = "Top 3 finale"
        elif 2 in top_placements:
            finale_format = "Top 2 finale"

        # cast / episode counts + air-date span -----------------------------
        cast_size = len(cs)
        episode_count = (_to_int(s.get("episode_count"))
                         if _to_int(s.get("episode_count")) is not None else len(eps))
        air_dates = sorted(d for d in (e.get("air_date") for e in eps)
                           if d and d not in BLANKS)
        premiere = air_dates[0] if air_dates else (
            s.get("premiere_date") if s.get("premiere_date") not in BLANKS else None)
        finale = air_dates[-1] if air_dates else None
        run_days = None
        avg_gap_days = None
        if len(air_dates) >= 2:
            d0 = datetime.date.fromisoformat(air_dates[0])
            d1 = datetime.date.fromisoformat(air_dates[-1])
            run_days = (d1 - d0).days
            gaps = []
            for a, b in zip(air_dates, air_dates[1:]):
                gaps.append((datetime.date.fromisoformat(b)
                             - datetime.date.fromisoformat(a)).days)
            if gaps:
                avg_gap_days = round(sum(gaps) / len(gaps), 1)

        # front_runner: most challenge wins (ties allowed) ------------------
        front_runner = None
        win_counts = [(cdisplay(c), _to_int(c.get("wins")) or 0) for c in cs]
        max_wins = max((w for _, w in win_counts), default=0)
        if max_wins > 0:
            fr_names = [nm for nm, w in win_counts if w == max_wins]
            front_runner = {"names": sorted(fr_names), "wins": max_wins}

        # lipsync_assassin: most lip syncs won within the season ------------
        lipsync_assassin = None
        ls_wins = Counter()
        for l in lss:
            w = l.get("winner_id")
            if w and w not in BLANKS:
                ls_wins[w] += 1
        if ls_wins:
            top = max(ls_wins.values())
            if top > 0:
                assassins = sorted(name(q) or q for q, n in ls_wins.items() if n == top)
                lipsync_assassin = {"names": assassins, "count": top}

        # never_bottom: top-4 finalists with 0 recorded bottoms -------------
        never_bottom = []
        for c in ranked:
            p = _to_int(c.get("placement"))
            if p is not None and 1 <= p <= 4:
                btm = _to_int(c.get("bottoms"))
                if btm == 0:
                    never_bottom.append(cdisplay(c))

        # cinderella: the winner won despite few maxi wins ------------------
        cinderella = None
        win_rows = [c for c in cs if c["queen_id"] == s.get("winner_id")] \
            or [c for c in cs if _to_int(c.get("placement")) == 1]
        if win_rows:
            wc = _to_int(win_rows[0].get("wins"))
            if wc is not None:
                cinderella = {"name": cdisplay(win_rows[0]), "wins": wc,
                              "low_win": wc <= 1}

        # comebacks: queens with a "returned" elimination event -------------
        comeback_ids = []
        for ev in evs:
            et = (ev.get("event_type") or "").lower()
            if "return" in et or "rtrn" in et:
                if ev["queen_id"] not in comeback_ids:
                    comeback_ids.append(ev["queen_id"])
        comebacks = [name(q) or q for q in comeback_ids]

        # double eliminations / non-eliminations ----------------------------
        elim_per_ep = Counter()
        for ev in evs:
            if (ev.get("event_type") or "").lower() == "eliminated":
                elim_per_ep[ev["episode_id"]] += 1
        double_elim_eps = sorted(e for e, n in elim_per_ep.items() if n > 1)
        # also catch double sashays coded only in lip_syncs
        sashay_eps = sorted({l["episode_id"] for l in lss
                             if l["result_type"] == "SASHAY"})
        double_eliminations = {
            "count": len(set(double_elim_eps) | set(sashay_eps)),
            "episodes": sorted(set(double_elim_eps) | set(sashay_eps)),
        }
        # non-eliminations: SHANTAY double saves + explicit saved events
        shantay_eps = sorted({l["episode_id"] for l in lss
                              if l["result_type"] == "SHANTAY"})
        saved_eps = sorted({ev["episode_id"] for ev in evs
                            if "saved" in (ev.get("event_type") or "").lower()
                            and ev["episode_id"] not in BLANKS})
        non_elim_eps = sorted(set(shantay_eps) | set(saved_eps))
        non_eliminations = {"count": len(non_elim_eps), "episodes": non_elim_eps}

        # disqualifications / withdrawals -----------------------------------
        dq = [name(ev["queen_id"]) or ev["queen_id"] for ev in evs
              if (ev.get("event_type") or "").lower() == "disqualified"]
        wd = [name(ev["queen_id"]) or ev["queen_id"] for ev in evs
              if (ev.get("event_type") or "").lower() in ("withdrew", "withdrawn")]
        # withdrawals also appear as WDR in progression
        wdr_prog = {p["queen_id"] for p in progression
                    if p["season_id"] == sid and p["status"] == "WDR"}
        for q in wdr_prog:
            nm = name(q)
            if nm and nm not in wd:
                wd.append(nm)
        disqualifications = {"count": len(dq), "names": sorted(dq)}
        withdrawals = {"count": len(wd), "names": sorted(wd)}

        # snatch_game -------------------------------------------------------
        snatch_game = None
        snatch_ep = None
        for e in eps:
            if e.get("main_challenge_type") == "Snatch Game" \
                    or "Snatch Game" in (e.get("title") or ""):
                snatch_ep = e
                break
        if snatch_ep:
            eid = snatch_ep["episode_id"]
            # challenge winner = queen(s) with WIN status that episode
            sg_winners = sorted({cdisplay(c) for c in cs for p in progression
                                 if p["episode_id"] == eid
                                 and p["queen_id"] == c["queen_id"]
                                 and p["status"] == "WIN"})
            char_count = sum(1 for r in roles_by_season.get(sid, [])
                             if r["episode_id"] == eid
                             and r["role_type"] == "SNATCH_CHARACTER")
            title = snatch_ep.get("title")
            snatch_game = {
                "episode_id": eid,
                "title": title if title not in BLANKS else None,
                "winner": sg_winners[0] if len(sg_winners) == 1 else (
                    sg_winners or None),
                "character_count": char_count,
            }

        # guest judges / song stats -----------------------------------------
        season_eids = {e["episode_id"] for e in eps}
        guest_names = set()
        for a in appearances:
            if a["appearance_type"] != "GUEST_JUDGE":
                continue
            if a["season_id"] == sid or a.get("episode_id") in season_eids:
                nm = (a.get("person_name") or "").strip()
                if nm and nm not in BLANKS:
                    guest_names.add(nm)
        guest_judges_count = len(guest_names)

        # distinct lip-sync songs + most-used song this season
        song_use = Counter()
        for e in eps:
            sgid = e.get("lip_sync_song_id")
            if sgid and sgid not in BLANKS:
                song_use[sgid] += 1
        for l in lss:
            sgid = l.get("song_id")
            if sgid and sgid not in BLANKS:
                song_use[sgid] += 1
        distinct_lipsync_songs = len(song_use)
        most_used_song = None
        if song_use:
            top_sid, top_n = song_use.most_common(1)[0]
            if top_n > 1 and song_title.get(top_sid):
                most_used_song = {"title": song_title[top_sid], "count": top_n}

        out[sid] = OrderedDict([
            ("winner", winner),
            ("runners_up", runners_up),
            ("miss_congeniality", mc),
            ("finale_format", finale_format),
            ("cast_size", cast_size),
            ("episode_count", episode_count),
            ("premiere", premiere),
            ("finale", finale),
            ("run_days", run_days),
            ("avg_gap_days", avg_gap_days),
            ("front_runner", front_runner),
            ("lipsync_assassin", lipsync_assassin),
            ("never_bottom", never_bottom),
            ("cinderella", cinderella),
            ("comebacks", comebacks),
            ("double_eliminations", double_eliminations),
            ("non_eliminations", non_eliminations),
            ("disqualifications", disqualifications),
            ("withdrawals", withdrawals),
            ("snatch_game", snatch_game),
            ("guest_judges_count", guest_judges_count),
            ("distinct_lipsync_songs", distinct_lipsync_songs),
            ("most_used_song", most_used_song),
        ])
    return out


def build_season_narratives(seasons):
    """Load editorial season prose from data/season_narratives.csv.

    If the file does not exist, create it with a header plus one empty row per
    season so a later stage can fill in the narratives. Returns a
    {season_id: narrative} map (only non-empty narratives are included).
    """
    npath = DATA / "season_narratives.csv"
    season_ids = [s["season_id"] for s in seasons]
    if not npath.exists():
        with open(npath, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["season_id", "narrative"])
            for sid in season_ids:
                w.writerow([sid, ""])
    narr = OrderedDict()
    with open(npath, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            text = (r.get("narrative") or "").strip()
            if text and text not in BLANKS:
                narr[r["season_id"]] = text
    return narr


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
