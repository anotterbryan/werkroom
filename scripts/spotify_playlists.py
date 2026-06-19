#!/usr/bin/env python3
"""
spotify_playlists.py — create & keep-in-sync Werkroom's Spotify playlists.

Builds PUBLIC playlists in YOUR account from the exact tracks in data/songs.csv:
  Masters:  All Lip Syncs · All Rusicals · All Cast Songs · All Ru-mixes
  Per season: one "<Season> Lip Syncs" playlist each.
Sync is ADDITIVE — it only adds tracks that are in our data but missing from the
playlist; it never deletes, so your manual edits/reorders are safe. Re-run anytime
after new Spotify links land.

Playlist IDs are recorded in data/playlists.csv (safe to commit — IDs only).
Your credentials + refresh token live in scripts/.spotify_auth.json (gitignored).

============================  ONE-TIME SETUP  ============================
1. Go to https://developer.spotify.com/dashboard  → "Create app".
   - App name: Werkroom (anything).  Redirect URI: http://127.0.0.1:8888/callback
   - Save. Open the app → Settings → copy the Client ID and Client Secret.
2. In Terminal:
     cd "~/Library/Mobile Documents/com~apple~CloudDocs/Art/Werkroom/files/rpdr-tracking"
     pip3 install requests
     python3 scripts/spotify_playlists.py auth --client-id YOUR_ID --client-secret YOUR_SECRET
   A browser opens; click Agree. It saves your token and you're done with setup.
3. Create / update all the playlists:
     python3 scripts/spotify_playlists.py sync
   (Re-run `sync` any time — it just adds what's new.)
   Then: git add data/playlists.csv && git commit -m "Spotify playlist IDs" && git push
==========================================================================
"""
import csv, json, sys, time, re, argparse, webbrowser, urllib.parse, http.server, threading
from pathlib import Path
try:
    import requests
except ImportError:
    sys.exit("Run:  pip3 install requests")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
AUTH = Path(__file__).resolve().parent / ".spotify_auth.json"
REDIRECT = "http://127.0.0.1:8888/callback"
SCOPE = "playlist-modify-public playlist-modify-private playlist-read-private"
API = "https://api.spotify.com/v1"
PREFIX = "Werkroom · "
BLANK = ("", "-")

# ----------------------------- auth -----------------------------
def _save(d): AUTH.write_text(json.dumps(d, indent=2)); AUTH.chmod(0o600)
def _load():
    if not AUTH.exists(): sys.exit("Not authorized yet — run the `auth` command first (see header).")
    return json.loads(AUTH.read_text())

def cmd_auth(args):
    cid, csec = args.client_id, args.client_secret
    code_holder = {}
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.urlparse(self.path).query
            code_holder.update(urllib.parse.parse_qs(q))
            self.send_response(200); self.end_headers()
            self.wfile.write(b"Werkroom: authorized. You can close this tab.")
        def log_message(self, *a): pass
    srv = http.server.HTTPServer(("127.0.0.1", 8888), H)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(
        {"client_id": cid, "response_type": "code", "redirect_uri": REDIRECT, "scope": SCOPE})
    print("Opening browser to authorize…\n", url)
    webbrowser.open(url)
    for _ in range(120):
        if "code" in code_holder: break
        time.sleep(1)
    if "code" not in code_holder: sys.exit("Timed out waiting for authorization.")
    tok = requests.post("https://accounts.spotify.com/api/token", data={
        "grant_type": "authorization_code", "code": code_holder["code"][0],
        "redirect_uri": REDIRECT, "client_id": cid, "client_secret": csec}).json()
    if "refresh_token" not in tok: sys.exit(f"Auth failed: {tok}")
    _save({"client_id": cid, "client_secret": csec, "refresh_token": tok["refresh_token"]})
    print("Authorized ✓  token saved to scripts/.spotify_auth.json")

def access_token():
    a = _load()
    r = requests.post("https://accounts.spotify.com/api/token", data={
        "grant_type": "refresh_token", "refresh_token": a["refresh_token"],
        "client_id": a["client_id"], "client_secret": a["client_secret"]}).json()
    if "access_token" not in r: sys.exit(f"Token refresh failed: {r}")
    return r["access_token"]

# ----------------------------- data -----------------------------
def read(name): return list(csv.DictReader(open(DATA / f"{name}.csv", encoding="utf-8")))
def has(s): return (s.get("spotify_track_id") or "") not in BLANK

def build_roster():
    songs = read("songs"); eps = read("episodes"); ls = read("lip_syncs"); seasons = read("seasons")
    ep_season = {e["episode_id"]: e["season_id"] for e in eps}
    ep_num = {e["episode_id"]: e.get("episode_number") or "0" for e in eps}
    # song_id -> {season_id: earliest episode number that season}
    song_seas = {}
    def note(song_id, eid):
        s_id = ep_season.get(eid, "")
        if not s_id: return
        try: n = int(re.sub(r"\D", "", ep_num.get(eid, "0")) or 0)
        except: n = 0
        d = song_seas.setdefault(song_id, {})
        if s_id not in d or n < d[s_id]: d[s_id] = n
    for e in eps:
        sg = e.get("lip_sync_song_id", "")
        if sg not in BLANK: note(sg, e["episode_id"])
    for r in ls:
        sg = r.get("song_id", "")
        if sg not in BLANK: note(sg, r["episode_id"])
    byid = {s["song_id"]: s for s in songs}
    def uri(s): return "spotify:track:" + s["spotify_track_id"]

    roster = []  # (key, name, description, [uris in order])
    cat = lambda s: (s.get("catalog") or "")
    lip = [s for s in songs if cat(s) in ("", "-", "LIPSYNC") and has(s)]
    roster.append(("master_lipsync", PREFIX + "All Lip Syncs",
                   "Every lip-sync song across all franchises. Auto-built by Werkroom.",
                   [uri(s) for s in lip]))
    roster.append(("master_rusical", PREFIX + "All Rusicals",
                   "Every Rusical / musical-challenge cast recording.",
                   [uri(s) for s in songs if cat(s) == "RUSICAL" and has(s)]))
    roster.append(("master_cast", PREFIX + "All Cast Songs",
                   "Girl-group, songwriting and other cast performance songs.",
                   [uri(s) for s in songs if cat(s) in ("CAST","GIRL_GROUP","SONGWRITING","QUEEN_RELEASE") and has(s)]))
    roster.append(("master_rumix", PREFIX + "All Ru-mixes",
                   "RuPaul's catalog used on the show.",
                   [uri(s) for s in songs if (s.get("is_rumix") or "").lower()=="yes" and has(s)]))
    # per-season lip syncs (ordered by episode number)
    label = {s["season_id"]: s.get("season_label") or s["season_id"] for s in seasons}
    for s in seasons:
        sid = s["season_id"]
        items = []
        for song_id, seas in song_seas.items():
            if sid in seas and song_id in byid and has(byid[song_id]):
                items.append((seas[sid], uri(byid[song_id])))
        if not items: continue
        items.sort(key=lambda x: x[0])
        roster.append((f"season_{sid}", f"{PREFIX}{label[sid]} Lip Syncs",
                       f"Lip-sync songs from {label[sid]}.", [u for _, u in items]))
    return roster

# ----------------------------- sync -----------------------------
def api(tok, method, path, **kw):
    for _ in range(6):
        r = requests.request(method, API + path, headers={"Authorization": f"Bearer {tok}"}, **kw)
        if r.status_code == 429:
            time.sleep(int(r.headers.get("Retry-After", "2")) + 1); continue
        return r
    return r

def existing_uris(tok, pid):
    out, url = set(), f"/playlists/{pid}/tracks?fields=items(track(uri)),next&limit=100"
    while url:
        r = api(tok, "GET", url).json()
        for it in r.get("items", []):
            t = (it or {}).get("track") or {}
            if t.get("uri"): out.add(t["uri"])
        nxt = r.get("next")
        url = nxt.replace(API, "") if nxt else None
    return out

def cmd_sync(args):
    tok = access_token()
    me = api(tok, "GET", "/me").json()
    uid = me["id"]
    print("Signed in as:", me.get("display_name") or uid)
    reg = DATA / "playlists.csv"
    rows = list(csv.DictReader(open(reg))) if reg.exists() else []
    ids = {r["key"]: r["spotify_playlist_id"] for r in rows if r.get("spotify_playlist_id") not in BLANK}
    out = []
    for key, name, desc, uris in build_roster():
        pid = ids.get(key)
        if not pid:
            r = api(tok, "POST", f"/users/{uid}/playlists",
                    json={"name": name, "public": True, "description": desc})
            if r.status_code not in (200, 201): print("  ! create failed", name, r.text[:120]); continue
            pid = r.json()["id"]; print(f"  + created {name}")
        have = existing_uris(tok, pid)
        missing = [u for u in uris if u not in have]
        seen = set(); missing = [u for u in missing if not (u in seen or seen.add(u))]
        for i in range(0, len(missing), 100):
            api(tok, "POST", f"/playlists/{pid}/tracks", json={"uris": missing[i:i+100]})
        print(f"  ✓ {name:42} {len(uris):4} tracks  (+{len(missing)} added)")
        out.append({"key": key, "name": name, "scope": key.split("_")[0],
                    "spotify_playlist_id": pid, "track_count": str(len(uris))})
    with open(reg, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["key","name","scope","spotify_playlist_id","track_count"])
        w.writeheader(); w.writerows(out)
    print(f"\nDone. {len(out)} playlists synced. IDs written to data/playlists.csv "
          f"(commit + push it so the site can embed them).")

# ----------------------------- cli -----------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("auth"); a.add_argument("--client-id", required=True); a.add_argument("--client-secret", required=True)
    sub.add_parser("sync")
    args = ap.parse_args()
    (cmd_auth if args.cmd == "auth" else cmd_sync)(args)
