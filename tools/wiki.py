#!/usr/bin/env python3
"""OSRS Wiki client with revision pinning (research and verification desks).

Why not just WebFetch? WebFetch returns a model-written *summary* of a page,
which loses exact numbers and cannot be cited immutably. This client reads
raw wikitext through the MediaWiki API and always reports the revision id,
so every claim can cite a permanent link:
    https://oldschool.runescape.wiki/w/index.php?oldid=<revid>
A verifier re-reading the same revid sees exactly what the researcher saw;
re-reading the *latest* revision shows whether the page has since changed.

Commands
  page TITLE [--grep REGEX] [--context N] [--section N] [--full]
  rev REVID [--grep REGEX] [--full]               fetch an exact pinned revision
  search QUERY [--limit N]
  new-pages --ns NAME --since YYYY-MM-DD          pages created in a namespace (e.g. Update)
  category NAME [--newest N]                      most recently added members (e.g. Quests)
  history TITLE [--limit N]                       recent revisions of a page

Set OSRS_UA to your own descriptive User-Agent if you like; the default is
generic and contains no personal data. Responses are cached under cache/wiki/.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CACHE, die, now_iso  # noqa: E402

API = "https://oldschool.runescape.wiki/api.php"
UA = __import__("os").environ.get("OSRS_UA", "osrs-guide-company/1.0 (personal guide tooling; python-urllib)")
CDIR = CACHE / "wiki"
_LAST = CDIR / ".last_request"


def _throttle():
    CDIR.mkdir(parents=True, exist_ok=True)
    try:
        wait = 1.0 - (time.time() - float(_LAST.read_text()))
        if wait > 0:
            time.sleep(wait)
    except (OSError, ValueError):
        pass
    _LAST.write_text(str(time.time()))


def api(params: dict) -> dict:
    params = {**params, "format": "json", "formatversion": "2"}
    url = API + "?" + urllib.parse.urlencode(params)
    _throttle()
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as exc:  # network policy, DNS, HTTP errors
        die(f"wiki API request failed: {exc}. If this is a sandbox, oldschool.runescape.wiki must be an allowed host.")
    if "error" in data:
        die(f"wiki API error: {data['error']}")
    return data


def permalink(revid: int) -> str:
    return f"https://oldschool.runescape.wiki/w/index.php?oldid={revid}"


def _emit(meta: dict, text: str, grep: str | None, context: int, full: bool):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", meta["title"])[:80]
    path = CDIR / f"{safe}@{meta['revid']}.wikitext"
    path.write_text(text, encoding="utf-8")
    meta = {**meta, "permalink": permalink(meta["revid"]), "retrieved": now_iso(), "cached": str(path),
            "chars": len(text)}
    print(json.dumps(meta, indent=2))
    lines = text.splitlines()
    if grep:
        rx = re.compile(grep, re.I)
        hits = [i for i, ln in enumerate(lines) if rx.search(ln)]
        shown = set()
        for i in hits:
            for j in range(max(0, i - context), min(len(lines), i + context + 1)):
                if j not in shown:
                    print(f"{j + 1:5d}| {lines[j]}")
                    shown.add(j)
            print("     ---")
        if not hits:
            print(f"(no lines match /{grep}/)")
    elif full:
        print(text)
    else:
        print("\n".join(lines[:80]))
        if len(lines) > 80:
            print(f"... ({len(lines) - 80} more lines; use --grep or --full)")


def _rev_query(extra: dict) -> tuple[dict, str]:
    data = api({"action": "query", "prop": "revisions", "rvprop": "ids|timestamp|content",
                "rvslots": "main", "redirects": "1", **extra})
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        die("page not found")
    pg = pages[0]
    rev = pg["revisions"][0]
    text = rev["slots"]["main"]["content"]
    return {"title": pg["title"], "pageid": pg.get("pageid"), "revid": rev["revid"],
            "rev_timestamp": rev["timestamp"]}, text


def cmd_page(a):
    extra = {"titles": a.title}
    if a.section is not None:
        extra["rvsection"] = str(a.section)
    meta, text = _rev_query(extra)
    _emit(meta, text, a.grep, a.context, a.full)


def cmd_rev(a):
    meta, text = _rev_query({"revids": str(a.revid)})
    _emit(meta, text, a.grep, a.context, a.full)


def cmd_search(a):
    data = api({"action": "query", "list": "search", "srsearch": a.query, "srlimit": str(a.limit)})
    for r in data["query"]["search"]:
        print(json.dumps({"title": r["title"], "timestamp": r.get("timestamp"),
                          "snippet": re.sub(r"<[^>]+>", "", r.get("snippet", ""))}))


def _ns_id(name: str) -> int:
    data = api({"action": "query", "meta": "siteinfo", "siprop": "namespaces"})
    for ns in data["query"]["namespaces"].values():
        if ns.get("name", "").lower() == name.lower() or ns.get("canonical", "").lower() == name.lower():
            return ns["id"]
    die(f"namespace {name!r} not found")


def cmd_new_pages(a):
    ns = _ns_id(a.ns)
    params = {"action": "query", "list": "logevents", "letype": "create", "lenamespace": str(ns),
              "ledir": "newer", "lestart": a.since + "T00:00:00Z", "lelimit": "500"}
    while True:
        data = api(params)
        for ev in data["query"]["logevents"]:
            print(json.dumps({"title": ev["title"], "created": ev["timestamp"]}))
        if "continue" not in data:
            break
        params.update(data["continue"])


def cmd_category(a):
    data = api({"action": "query", "list": "categorymembers", "cmtitle": f"Category:{a.name}",
                "cmsort": "timestamp", "cmdir": "desc", "cmlimit": str(a.newest), "cmprop": "title|timestamp"})
    for m in data["query"]["categorymembers"]:
        print(json.dumps({"title": m["title"], "added_to_category": m.get("timestamp")}))


def cmd_history(a):
    data = api({"action": "query", "prop": "revisions", "titles": a.title, "rvlimit": str(a.limit),
                "rvprop": "ids|timestamp|user|comment|size"})
    pg = data["query"]["pages"][0]
    for r in pg.get("revisions", []):
        print(json.dumps({"revid": r["revid"], "timestamp": r["timestamp"], "user": r.get("user"),
                          "comment": r.get("comment", "")[:200], "permalink": permalink(r["revid"])}))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("page"); s.add_argument("title"); s.add_argument("--grep"); s.add_argument("--context", type=int, default=2)
    s.add_argument("--section", type=int); s.add_argument("--full", action="store_true"); s.set_defaults(f=cmd_page)
    s = sp.add_parser("rev"); s.add_argument("revid", type=int); s.add_argument("--grep"); s.add_argument("--context", type=int, default=2)
    s.add_argument("--full", action="store_true"); s.set_defaults(f=cmd_rev)
    s = sp.add_parser("search"); s.add_argument("query"); s.add_argument("--limit", type=int, default=10); s.set_defaults(f=cmd_search)
    s = sp.add_parser("new-pages"); s.add_argument("--ns", required=True); s.add_argument("--since", required=True); s.set_defaults(f=cmd_new_pages)
    s = sp.add_parser("category"); s.add_argument("name"); s.add_argument("--newest", type=int, default=30); s.set_defaults(f=cmd_category)
    s = sp.add_parser("history"); s.add_argument("title"); s.add_argument("--limit", type=int, default=10); s.set_defaults(f=cmd_history)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
