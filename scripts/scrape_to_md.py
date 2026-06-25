#!/usr/bin/env python3
"""
scrape_to_md.py — a free, self-hosted "Firecrawl-lite": fetch a web page and save
it as CLEAN Markdown, with data tables preserved as raw HTML (so the Werkroom
parser can read progress charts / lip-sync tables exactly).

Built for SERVER-RENDERED wikis — Fandom (rupaulsdragrace.fandom.com) and
Wikipedia — which is all the Drag Race data needs. No API key, no auth, no cost.
(For heavy-JavaScript sites it won't render JS; use a browser/Firecrawl there.)

USAGE (run on your Mac — it needs outbound web access):
    pip3 install requests beautifulsoup4 markdownify
    # one page:
    python3 scripts/scrape_to_md.py "https://rupaulsdragrace.fandom.com/wiki/Drag_Race_Down_Under_(Season_1)" --out "../../Fandom/Down Under/Fandom"
    # many pages from a list (one URL per line):
    python3 scripts/scrape_to_md.py --urls urls.txt --out "../../Fandom/Down Under/Fandom"

Output: one <Page Title>.md per URL, with YAML frontmatter (title, source, fetched).
"""
import sys, re, time, argparse, datetime
from pathlib import Path
try:
    import requests
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md
except ImportError:
    sys.exit("Install deps:  pip3 install requests beautifulsoup4 markdownify")

HEADERS = {"User-Agent": "Mozilla/5.0 (Werkroom scrape_to_md)"}
JUNK = [".toc", ".mw-editsection", ".navbox", "script", "style", ".reference",
        ".references", ".printfooter", ".mw-jump-link", ".noprint",
        ".wds-tabber__tabs", "#References", ".mw-references-wrap"]

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text

def main_content(soup):
    # MediaWiki (Fandom + Wikipedia) article body; fall back to <main>/<article>.
    for sel in [".mw-parser-output", "#mw-content-text", "main", "article"]:
        el = soup.select_one(sel)
        if el:
            return el
    return soup.body or soup

def to_markdown(html, url):
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.get_text(strip=True) if soup.title else "page")
    title = re.split(r"\s*[\|–-]\s*", title)[0].strip() or "page"
    body = main_content(soup)
    for sel in JUNK:
        for el in body.select(sel):
            el.decompose()
    # preserve tables exactly (markdownify would flatten colspan/rowspan)
    tables = []
    for i, tbl in enumerate(body.find_all("table")):
        tables.append(str(tbl))
        tbl.replace_with(f"ZZTABLEMARKER{i}ZZ")  # alphanumeric -> not escaped
    text = md(str(body), heading_style="ATX")
    for i, raw in enumerate(tables):
        text = text.replace(f"ZZTABLEMARKER{i}ZZ", "\n" + raw + "\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    fm = (f"---\ntitle: \"{title}\"\nsource: \"{url}\"\n"
          f"fetched: {datetime.date.today().isoformat()}\ntags:\n  - clippings\n---\n")
    return title, fm + text + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls_pos", nargs="*", help="one or more URLs")
    ap.add_argument("--urls", help="file with one URL per line")
    ap.add_argument("--out", default=".", help="output directory")
    a = ap.parse_args()
    urls = list(a.urls_pos)
    if a.urls:
        urls += [l.strip() for l in open(a.urls) if l.strip() and not l.startswith("#")]
    if not urls:
        sys.exit("Provide URL(s) or --urls file.")
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ok = bad = 0
    for u in urls:
        try:
            title, text = to_markdown(fetch(u), u)
            safe = re.sub(r'[/\\:*?"<>|]', "_", title)
            (out / f"{safe}.md").write_text(text, encoding="utf-8")
            ok += 1; print(f"  ✓ {title}  ({len(text)//1024}KB)")
            time.sleep(0.5)
        except Exception as e:
            bad += 1; print(f"  ✗ {u}  {e}")
    print(f"\nwrote {ok} markdown file(s) to {out}" + (f"; {bad} failed" if bad else ""))

if __name__ == "__main__":
    main()
