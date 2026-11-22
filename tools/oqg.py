#!/usr/bin/env python3
"""Where the owner is in the OSRS Wiki's Optimal quest guide (tools only, no agents).

  python3 tools/oqg.py status <rsn> [--next 5]        position, next quests, danger tier, Defence-cap check
  python3 tools/oqg.py mark <rsn> --through "<row>" [--skip "<row>" ...] [--done "<row>" ...]
                                                     record progress when WikiSync has no data

Sources (each output line says which one was used):
  - Order and XP rewards: the wiki page "Optimal quest guide", revision-pinned (cache/wiki).
  - Quest difficulty: each next quest's own wiki page (|difficulty = ...), cached by revision.
  - Completed quests: WikiSync (sync.runescape.wiki, RuneLite WikiSync plugin) if it returns data,
    else profiles/<rsn>.json quests_completed plus the profile's "oqg" marker.
Danger = policy/danger-calibration.json quest tiers (with-prep, game-relative). +5 if below the
quest's recommended stats is NOT computed here; the quest page lists them.
Defence XP is read from the guide's {{Optimal quest|defence=N}} cell. Rows whose notes mention a
choice (lamp, "choose", Daero, etc.) are flagged: the guide's choice is not the owner's build.
Leads, not verified facts: anything that goes into a guide still goes through the Fact Verifier.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, die, load_json, now_iso, save_json, today  # noqa: E402
import wiki  # noqa: E402
import xp as xpmod  # noqa: E402

PAGE = "Optimal quest guide"
META = ROOT / "cache" / "wiki" / "quest_meta.json"
# A Defence reward counts as the owner's choice only when the guide's note ties a choice to Defence
# (e.g. "Choose Defence for both", Daero's Attack/Defence option). A lamp spent on another skill
# (King's Ransom: "use the lamp on Slayer") leaves the Defence reward fixed.
CHOICE = re.compile(r"(choose|choice|lamp|Daero|book of knowledge)[^\n]{0,80}Defence|Defence[^\n]{0,40}(choose|choice|lamp)", re.I)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("&", "and"))


def guide() -> tuple[dict, list[dict]]:
    meta, text = wiki._rev_query({"titles": PAGE})
    rows = []
    for chunk in re.split(r'\n\|- data-rowid="', text)[1:]:
        rid = chunk.split('"', 1)[0]
        cell = re.search(r"\{\{Optimal quest\|([^}]*)\}\}", chunk)
        rewards = {}
        if cell:
            for k, v in re.findall(r"([a-z_]+)=(\d+)", cell.group(1)):
                rewards[k] = int(v)
        qp = re.search(r"\{\{Optimal quest/qp\|(\d+)\}\}", chunk)
        lines = chunk.split("\n|")
        title_cell = lines[1] if len(lines) > 1 else rid
        kind = "miniquest" if "(miniquest)" in title_cell else ("activity" if "#" in rid or not qp or qp.group(1) == "0" else "quest")
        notes = lines[5] if len(lines) > 5 else ""
        rows.append({"row": rid, "kind": kind, "qp": int(qp.group(1)) if qp else 0, "xp": rewards,
                     "defence_choice": bool(rewards.get("defence")) and bool(CHOICE.search(notes))})
    return meta, rows


def wikisync(rsn: str) -> tuple[set[str] | None, str]:
    url = f"https://sync.runescape.wiki/runelite/player/{urllib.parse.quote(rsn)}/STANDARD"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": wiki.UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
        done = {norm(q) for q, v in (d.get("quests") or {}).items() if v == 2}
        return done, f"WikiSync ({d.get('timestamp', 'no timestamp')})"
    except Exception as exc:
        return None, f"WikiSync unavailable ({exc}); profile used"


def completed(prof: dict, rows: list[dict], rsn: str) -> tuple[set[str], str]:
    done, src = wikisync(rsn)
    if done:
        return done, src
    done = {norm(q) for q in prof.get("quests_completed", [])}
    m = prof.get("oqg") or {}
    if m.get("through"):
        names = [r["row"] for r in rows]
        if m["through"] in names:
            skipped = {norm(s) for s in m.get("skipped", [])}
            done |= {norm(n) for n in names[:names.index(m["through"]) + 1] if norm(n) not in skipped}
    done |= {norm(x) for x in m.get("done", [])}
    note = f"profile quests_completed ({len(prof.get('quests_completed', []))})"
    if m.get("through"):
        note += f" + marked done through '{m['through']}' on {m.get('marked', '?')}"
    return done, note + f"; {src}"


def difficulty(title: str) -> tuple[str | None, int | None]:
    cache = load_json(META) if META.exists() else {}
    base = title.split("#")[0]
    if base in cache:
        return cache[base]["difficulty"], cache[base]["revid"]
    try:
        meta, text = wiki._rev_query({"titles": base})
    except SystemExit:
        return None, None
    m = re.search(r"\|\s*difficulty\s*=\s*([A-Za-z]+)", text)
    diff = m.group(1).capitalize() if m else None
    cache[base] = {"difficulty": diff, "revid": meta["revid"], "retrieved": now_iso()}
    META.parent.mkdir(parents=True, exist_ok=True)
    save_json(META, cache)
    return diff, meta["revid"]


def status_lines(rsn: str, prof: dict, n: int = 5) -> list[str]:
    meta, rows = guide()
    done, src = completed(prof, rows, rsn)
    tiers = load_json(ROOT / "policy" / "danger-calibration.json")["quest_tiers"]["tiers"]
    todo = [r for r in rows if norm(r["row"]) not in done and norm(r["row"].split("#")[0]) not in done]
    quests = [r for r in rows if r["kind"] == "quest"]
    qdone = sum(1 for r in quests if r not in todo)
    out = [f"Optimal quest guide (wiki rev {meta['revid']}): {qdone}/{len(quests)} quests done. Progress source: {src}"]
    if not todo:
        return out + ["   all rows done"]
    first = rows.index(todo[0])
    later_done = sum(1 for r in rows[first:] if r not in todo)
    out.append(f"   position: row {first + 1}/{len(rows)}, '{todo[0]['row']}'"
               + (f" ({later_done} later rows already done)" if later_done else ""))
    for r in todo[:n]:
        if r["kind"] in ("activity", "miniquest"):
            ds = f"no quest tier ({r['kind']})"
        else:
            diff, rev = difficulty(r["row"])
            ds = f"danger {tiers[diff]} ({diff}, rev {rev})" if diff in tiers else f"difficulty unknown (rev {rev})"
        d = r["xp"].get("defence")
        dtxt = ""
        if d:
            dtxt = f"  | Defence +{d:,}" + (" (CHOICE in guide notes: pick a non-Defence skill if offered)" if r["defence_choice"] else "")
        out.append(f"   next: {r['row']} [{r['kind']}] {ds}{dtxt}")
    cap = (prof.get("build") or {}).get("skill_caps", {}).get("Defence")
    if cap:
        cur = prof.get("skill_xp", {}).get("Defence") or xpmod.xp_for(prof["stats"].get("Defence", 1))
        limit = xpmod.xp_for(cap + 1) - 1
        def first_breach(include_choice: bool):
            run, hit = cur, None
            for r in todo:
                if r["xp"].get("defence") and (include_choice or not r["defence_choice"]):
                    run += r["xp"]["defence"]
                    if run > limit and hit is None:
                        hit = r["row"]
            return hit, run
        all_b, all_run = first_breach(True)
        fix_b, fix_run = first_breach(False)
        out.append(f"   Defence: {cur:,} XP, cap {cap} = {limit:,} XP, headroom {limit - cur:,}.")
        out.append(f"   - fixed quest Defence rewards ahead: +{fix_run - cur:,}"
                   + (f" -> CAP PASSED at '{fix_b}'" if fix_b else f" -> Defence {xpmod.level_for(fix_run)} at the end, within cap"))
        out.append("   - choosable rewards are the owner's pick (never Defence per build); the guide's own choices are ignored")
        ahead = [f"{r['row']} +{r['xp']['defence']:,}" for r in todo if r["xp"].get("defence") and not r["defence_choice"]]
        if ahead:
            out.append("   fixed Defence rewards ahead: " + ", ".join(ahead))
    out.append("   leads only: confirm rewards and recommended stats on each quest page")
    return out


def cmd_status(a):
    prof = load_json(ROOT / "profiles" / f"{a.rsn}.json")
    print("\n".join(status_lines(a.rsn, prof, a.next)))


def cmd_mark(a):
    pf = ROOT / "profiles" / f"{a.rsn}.json"
    prof = load_json(pf)
    _, rows = guide()
    names = [r["row"] for r in rows]
    for x in [a.through, *a.skip, *a.done]:
        if x and x not in names:
            die(f"'{x}' is not a row of the Optimal quest guide (check spelling: {', '.join(n for n in names if norm(x)[:5] in norm(n))[:200]})")
    prof["oqg"] = {"through": a.through, "skipped": a.skip, "done": a.done, "marked": today(), "source": "owner"}
    save_json(pf, prof)
    print(f"marked: done through '{a.through}' (row {names.index(a.through) + 1}), skipped {len(a.skip)}, extra done {len(a.done)}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("status"); s.add_argument("rsn"); s.add_argument("--next", type=int, default=5); s.set_defaults(f=cmd_status)
    s = sp.add_parser("mark"); s.add_argument("rsn"); s.add_argument("--through", required=True)
    s.add_argument("--skip", action="append", default=[]); s.add_argument("--done", action="append", default=[])
    s.set_defaults(f=cmd_mark)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    import urllib.parse  # noqa: F401
    main()
