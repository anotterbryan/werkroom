#!/usr/bin/env python3
"""
build_knowledge_pack.py -- Compile data/*.csv into site/kb/facts.json, the
retrieval corpus for the Ask-the-Library chatbot (served by GitHub Pages,
fetched + cached by the Cloudflare Worker in chatbot/).

Each fact: {"t": text, "k": keywords, "l": site route}. Pure & deterministic.
Run after any data change, alongside build_site_data.py.
"""
import csv, json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "site" / "kb" / "facts.json"
B = ("", "-")

def rd(n):
    with open(DATA / f"{n}.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))

def nb(v):  # non-blank
    return v not in B and v is not None

def main():
    queens, seasons = rd("queens"), rd("seasons")
    cont, eps = rd("contestants"), rd("episodes")
    prog, songs = rd("progression"), rd("songs")
    ls, ev = rd("lip_syncs"), rd("elimination_events")
    panel, app = rd("panel"), rd("appearances")
    roles = rd("episode_roles")

    qn = {q["queen_id"]: q["drag_name"] for q in queens}
    sl = {s["season_id"]: s["season_label"] for s in seasons}
    epl = {e["episode_id"]: e for e in eps}
    facts = []
    def F(t, k, l):
        facts.append({"t": t, "k": k, "l": l})

    # ---- queens ----
    bycq = defaultdict(list)
    for c in cont:
        bycq[c["queen_id"]].append(c)
    snatch = defaultdict(list)
    cid2c = {c["contestant_id"]: c for c in cont}
    for r in roles:
        if r["role_type"] == "SNATCH_CHARACTER":
            c = cid2c.get(r["contestant_id"])
            if c: snatch[c["queen_id"]].append((r["episode_id"], r["role_detail"]))
    lsq = defaultdict(lambda: [0, 0])
    for l in ls:
        for q in (l["queen_a_id"], l["queen_b_id"]):
            if nb(q): lsq[q][1] += 1
        if nb(l["winner_id"]): lsq[l["winner_id"]][0] += 1
    for q in queens:
        qid = q["queen_id"]
        runs = []
        for c in sorted(bycq[qid], key=lambda x: x["season_id"]):
            r = sl.get(c["season_id"], c["season_id"])
            if nb(c["placement"]):
                r += f" (placed #{c['placement']}" + (", winner" if c["placement"] == "1" else "") + ")"
            if nb(c["drag_name_used"]):
                r += f" as {c['drag_name_used']}"
            runs.append(r)
        bits = [f"{q['drag_name']} competed on {'; '.join(runs)}." if runs else f"{q['drag_name']} is in the database."]
        if nb(q["legal_name"]): bits.append(f"Legal name {q['legal_name']}.")
        if nb(q["birthdate"]): bits.append(f"Born {q['birthdate']}.")
        if nb(q["hometown"]): bits.append(f"Hometown {q['hometown']}.")
        ages = [c["age_at_filming"] for c in bycq[qid] if nb(c.get("age_at_filming"))]
        if ages: bits.append(f"Age at filming: {', '.join(ages)}.")
        earn = sum(int(c["earnings"]) for c in bycq[qid] if nb(c.get("earnings")))
        if earn: bits.append(f"Documented prize money ${earn:,}.")
        w, t = lsq[qid]
        if t: bits.append(f"Lip syncs: {t} performed, {w} won.")
        for eid, ch in snatch[qid]:
            bits.append(f"Played {ch} in Snatch Game ({eid}).")
        if any(c["miss_congeniality"] == "Yes" for c in bycq[qid]):
            bits.append("Named Miss Congeniality.")
        F(" ".join(bits), q["drag_name"].lower(), f"queen:{qid}")

    # ---- seasons ----
    for s in seasons:
        sid = s["season_id"]
        cast = [c for c in cont if c["season_id"] == sid]
        bits = [f"{s['season_label']} ({s['franchise']}, {sid}) aired on {s['platform']}, premiered {s['premiere_date']}, {s['episode_count']} episodes, cast of {len(cast)}."]
        if nb(s["winner_id"]): bits.append(f"Winner: {qn.get(s['winner_id'])}.")
        rups = [qn[c["queen_id"]] for c in cast if c["placement"] == "2"]
        if rups: bits.append(f"Runner-up: {', '.join(rups)}.")
        if nb(s["miss_congeniality_id"]): bits.append(f"Miss Congeniality: {qn.get(s['miss_congeniality_id'])}.")
        if nb(s["cash_prize"]): bits.append(f"Grand prize ${int(s['cash_prize']):,}.")
        pj = [p["person_name"] for p in panel if p["season_id"] == sid]
        if pj: bits.append(f"Panel: {', '.join(pj)}.")
        F(" ".join(bits), f"{s['season_label']} {sid} {s['franchise']}".lower(), f"season:{sid}")

    # ---- episodes ----
    fw = {(e["episode_id"], e["queen_id"]): e["farewell"] for e in ev if nb(e.get("farewell"))}
    gj = defaultdict(list)
    for a in app:
        if a["appearance_type"] == "GUEST_JUDGE" and nb(a["episode_id"]):
            gj[a["episode_id"]].append(a["person_name"])
    sng = {s["song_id"]: s for s in songs}
    lsbe = defaultdict(list)
    for l in ls: lsbe[l["episode_id"]].append(l)
    for e in eps:
        eid = e["episode_id"]
        bits = [f"{sl.get(e['season_id'])} episode {e['episode_number']}" +
                (f' "{e["title"]}"' if nb(e["title"]) else "") +
                (f" aired {e['air_date']}." if nb(e["air_date"]) else ".")]
        if nb(e["main_challenge"]): bits.append(f"Challenge: {e['main_challenge']} ({e['main_challenge_type']}).")
        if nb(e["runway_theme"]): bits.append(f"Runway: {e['runway_theme']}.")
        if gj[eid]: bits.append(f"Guest judges: {', '.join(gj[eid])}.")
        for l in lsbe[eid]:
            s = sng.get(l["song_id"], {})
            pair = " vs ".join(qn.get(x, "?") for x in (l["queen_a_id"], l["queen_b_id"]) if nb(x))
            line = f"Lip sync: {pair} to \"{s.get('title','?')}\" by {s.get('artist','?')}"
            if nb(l["winner_id"]): line += f"; {qn.get(l['winner_id'])} won"
            line += f" ({l['result_type']})."
            bits.append(line)
        if nb(e["eliminated_id"]):
            bits.append(f"Eliminated: {qn.get(e['eliminated_id'])}.")
            m = fw.get((eid, e["eliminated_id"]))
            if m: bits.append(f"Mirror message: \"{m}\"")
        F(" ".join(bits), f"{eid} {e.get('title','')}".lower(), f"season:{e['season_id']}")

    # ---- songs ----
    use = defaultdict(set)
    for e in eps:
        if nb(e["lip_sync_song_id"]): use[e["lip_sync_song_id"]].add(e["episode_id"])
    for l in ls:
        if nb(l["song_id"]): use[l["song_id"]].add(l["episode_id"])
    for s in songs:
        if not nb(s["title"]): continue
        bits = [f"\"{s['title']}\" by {s['artist']} was lip-synced in {', '.join(sorted(use[s['song_id']]))}."]
        if s.get("is_rumix") == "Yes": bits.append("It is a RuPaul track (Ru-mix).")
        F(" ".join(bits), f"{s['title']} {s['artist']}".lower(), "music")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"v": 1, "facts": facts}, separators=(",", ":"), ensure_ascii=False)
    OUT.write_text(payload, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(facts)} facts, {len(payload):,} bytes")

if __name__ == "__main__":
    main()
