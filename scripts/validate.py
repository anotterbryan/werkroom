#!/usr/bin/env python3
"""
validate.py  --  Enforce the data invariants for the RPDR Tracking database.

Run after any edit to data/*.csv. Prints a report and exits non-zero if any check
fails, so it doubles as the CI gate (.github/workflows/validate.yml).

Checks:
  1. Primary keys unique and present.
  2. Foreign keys resolve (queen / season / episode / song references).
  3. Ground truth: for episodes whose lip sync is a single NORMAL no-save result,
     the lip-sync loser equals episodes.eliminated_id.
  4. Tally formula: contestants wins/highs/lows/bottoms == counts derived from
     progression (wins=WIN, highs=HIGH, lows=LOW, bottoms=BTM+ELIM).
  5. Song references resolve and songs.times_used == distinct episodes (episodes
     UNION lip_syncs) the song appears in.

Usage:
    python scripts/validate.py            # full report
    python scripts/validate.py -q         # only failures + final status
"""
import csv, sys, argparse
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BLANKS = ("", "-")

PK = {
    "queens": "queen_id", "seasons": "season_id", "contestants": "contestant_id",
    "episodes": "episode_id", "progression": "progression_id", "songs": "song_id",
    "lip_syncs": "lip_sync_id", "elimination_events": "event_id",
    "panel": "panel_id", "appearances": "appearance_id",
}


def load(name):
    with open(DATA / f"{name}.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args()

    t = {n: load(n) for n in PK}
    results = []  # (name, ok, detail)

    def check(name, bad, fmt=lambda x: str(x), limit=8):
        ok = not bad
        if ok:
            detail = "ok"
        else:
            shown = "; ".join(fmt(b) for b in bad[:limit])
            more = f" (+{len(bad) - limit} more)" if len(bad) > limit else ""
            detail = f"{len(bad)} problem(s): {shown}{more}"
        results.append((name, ok, detail))

    # 1. primary keys -------------------------------------------------------
    for n, key in PK.items():
        ids = [r[key] for r in t[n]]
        dupes = [k for k, c in Counter(ids).items() if c > 1]
        blanks = sum(1 for i in ids if i in BLANKS)
        check(f"PK unique/present: {n}.{key}",
              ([f"dup {d}" for d in dupes] + ([f"{blanks} blank"] if blanks else [])))

    # build id sets for FK checks
    qids = {r["queen_id"] for r in t["queens"]}
    sids = {r["season_id"] for r in t["seasons"]}
    eids = {r["episode_id"] for r in t["episodes"]}
    sgids = {r["song_id"] for r in t["songs"]}
    cids = {r["contestant_id"] for r in t["contestants"]}

    def fk(rows, field, valid, allow_blank=True):
        bad = []
        for r in rows:
            v = r.get(field, "")
            if v in BLANKS:
                if not allow_blank:
                    bad.append(f"{field} blank")
                continue
            if v not in valid:
                bad.append(f"{field}={v}")
        return bad

    # 2. foreign keys -------------------------------------------------------
    check("FK contestants.queen_id -> queens", fk(t["contestants"], "queen_id", qids, False))
    check("FK contestants.season_id -> seasons", fk(t["contestants"], "season_id", sids, False))
    check("FK episodes.season_id -> seasons", fk(t["episodes"], "season_id", sids, False))
    check("FK episodes.eliminated_id -> queens", fk(t["episodes"], "eliminated_id", qids))
    check("FK episodes.lip_sync_song_id -> songs", fk(t["episodes"], "lip_sync_song_id", sgids))
    check("FK progression.contestant_id -> contestants", fk(t["progression"], "contestant_id", cids, False))
    check("FK progression.episode_id -> episodes", fk(t["progression"], "episode_id", eids, False))
    check("FK lip_syncs.episode_id -> episodes", fk(t["lip_syncs"], "episode_id", eids, False))
    check("FK lip_syncs.song_id -> songs", fk(t["lip_syncs"], "song_id", sgids))
    for f in ("queen_a_id", "queen_b_id", "winner_id", "loser_id"):
        check(f"FK lip_syncs.{f} -> queens", fk(t["lip_syncs"], f, qids))
    check("FK elimination_events.queen_id -> queens", fk(t["elimination_events"], "queen_id", qids, False))
    check("FK elimination_events.episode_id -> episodes", fk(t["elimination_events"], "episode_id", eids))
    check("FK panel.season_id -> seasons", fk(t["panel"], "season_id", sids, False))
    check("FK appearances.season_id -> seasons", fk(t["appearances"], "season_id", sids, False))
    check("FK appearances.episode_id -> episodes", fk(t["appearances"], "episode_id", eids))

    # 3. ground truth: single NORMAL no-save loser == eliminated_id ----------
    epmap = {e["episode_id"]: e for e in t["episodes"]}
    ls_by_ep = defaultdict(list)
    for r in t["lip_syncs"]:
        ls_by_ep[r["episode_id"]].append(r)
    gt_bad = []
    for eid, rows in ls_by_ep.items():
        normals = [r for r in rows if r["result_type"] == "NORMAL" and r["was_save"] == "No"]
        if len(normals) == 1 and len(rows) == 1:
            loser = normals[0]["loser_id"]
            elim = epmap.get(eid, {}).get("eliminated_id", "")
            if loser not in BLANKS and elim not in BLANKS and loser != elim:
                gt_bad.append(f"{eid}: loser {loser} != eliminated {elim}")
    check("ground truth: NORMAL no-save loser == eliminated_id", gt_bad)

    # 4. tally formula ------------------------------------------------------
    pc = defaultdict(Counter)
    for p in t["progression"]:
        pc[p["contestant_id"]][p["status"]] += 1
    tally_bad = []
    for c in t["contestants"]:
        s = pc[c["contestant_id"]]
        want = (s["WIN"], s["HIGH"], s["LOW"], s["BTM"] + s["ELIM"])
        got = tuple(int(c[k]) if c[k] not in BLANKS else 0
                    for k in ("wins", "highs", "lows", "bottoms"))
        if want != got:
            tally_bad.append(f"{c['contestant_id']} W/H/L/B want {want} got {got}")
    check("tally formula (W/H/L/B from progression)", tally_bad)

    # 5. song times_used ----------------------------------------------------
    song_eps = defaultdict(set)
    for e in t["episodes"]:
        if e["lip_sync_song_id"] not in BLANKS:
            song_eps[e["lip_sync_song_id"]].add(e["episode_id"])
    for r in t["lip_syncs"]:
        if r["song_id"] not in BLANKS:
            song_eps[r["song_id"]].add(r["episode_id"])
    tu_bad = []
    for s in t["songs"]:
        want = len(song_eps.get(s["song_id"], set()))
        got = int(s["times_used"]) if s["times_used"] not in BLANKS else 0
        if want != got:
            tu_bad.append(f"{s['song_id']} times_used want {want} got {got}")
    check("songs.times_used == distinct episodes", tu_bad)

    # ---- report -----------------------------------------------------------
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        if ok and args.quiet:
            continue
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\n{passed}/{len(results)} checks passed.")
    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
