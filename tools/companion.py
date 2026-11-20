#!/usr/bin/env python3
"""Daily companion check-in (no agents, a few cheap requests).

  python3 tools/companion.py today <rsn>      daily briefing; appends a stats snapshot to the profile
  python3 tools/companion.py where <rsn>      where you are in each active guide, plus the next decision point

What `today` does:
  1. Reads profiles/<rsn>.json (the persistent account profile).
  2. Fetches the Hardcore Worlds hiscores. Changes since the last snapshot are listed;
     a new skill level is shown with its exact XP.
  3. Lists OSRS Wiki Update: pages created since the last check-in. These are leads
     only: anything relevant is routed to the Patch Sentinel (/osrs-refresh).
  4. For each active guide: current step and route position, the next decision
     point with its options and danger scores, and the levels to go.
Writes nothing except the snapshot appended to the profile.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, die, load_json, now_iso, save_json, today  # noqa: E402
import xp as xpmod  # noqa: E402

PROFILES = ROOT / "profiles"


def _run(*args) -> str:
    r = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[:300])
    return r.stdout


def hiscores(rsn: str) -> dict | None:
    try:
        return json.loads(_run("tools/hiscores.py", "lookup", rsn))
    except Exception as exc:  # network or player not ranked
        print(f"(hiscores unavailable: {exc})")
        return None


def new_updates(since: str) -> list[dict]:
    try:
        out = _run("tools/wiki.py", "new-pages", "--ns", "Update", "--since", since)
        return [json.loads(l) for l in out.splitlines() if l.strip()]
    except Exception as exc:
        print(f"(update sweep unavailable: {exc})")
        return []


def where(profile: dict, skill_xp_override: dict | None = None) -> list[str]:
    lines = []
    for job in profile.get("active_guides", []):
        cpath = ROOT / "jobs" / job / "content.json"
        src = cpath if cpath.exists() else None
        if src is None:
            plan, calc = ROOT / "jobs" / job / "plan.json", ROOT / "jobs" / job / "calc.json"
            if not (plan.exists() and calc.exists()):
                lines.append(f"[{job}] not built yet")
                continue
            plan, calc = load_json(plan), load_json(calc)
            skill = plan["target"]["skill"]
            routes = {r["route_id"]: {**r, "calc": {s["step_id"]: s for s in calc["routes"][r["route_id"]]["steps"]}}
                      for r in plan["routes"]}
            steps = {s["step_id"]: s for s in plan["steps"]}
            dps = plan.get("decision_points", [])
            scores = {}
        else:
            c = load_json(cpath)
            skill = c["meta"]["skill"]
            routes = {r["route_id"]: r for r in c["routes"]}
            steps = {s["step_id"]: s for s in c["steps"]}
            dps = c.get("decision_points", [])
            scores = {s["step_id"]: s["risk"]["score"]["residual_ds"] for s in c["steps"]}
        cur_xp = (skill_xp_override or {}).get(skill) or profile.get("skill_xp", {}).get(skill) \
            or xpmod.xp_for(profile["stats"].get(skill, 1))
        lvl = xpmod.level_for(cur_xp)
        lines.append(f"[{job}] {skill} {lvl} ({cur_xp:,} XP)")
        for rid, r in routes.items():
            here = next((sid for sid in r["step_ids"] if r["calc"].get(sid, {}).get("end_xp", 0) > cur_xp), None)
            if here:
                st = steps[here]
                ds = f", danger {scores[here]}" if here in scores else ""
                lines.append(f"   {rid:9s} now: {here} {st['title']}{ds}")
        upcoming = sorted([d for d in dps if d.get("until_level", 100) > lvl], key=lambda d: d["at_level"])[:1]
        for d in upcoming:
            lines.append(f"   next decision ({d['dp_id']}, from {d['at_level']}): {d['question']}")
            for o in d["options"]:
                rec = " (recommended)" if o["option_id"] == d["recommended"] else ""
                lines.append(f"      {o['option_id']}. {o['title']}{rec}")
    return lines


def cmd_today(a):
    pf = PROFILES / f"{a.rsn}.json"
    if not pf.exists():
        die(f"no profile {pf}; create one through intake")
    prof = load_json(pf)
    last = prof["snapshots"][-1] if prof.get("snapshots") else None
    print(f"=== OSRS Companion · {a.rsn} · {today()} ===")
    hs = hiscores(a.rsn)
    if hs:
        changes = []
        base = (last or {}).get("stats") or prof["stats"]
        for sk, lv in hs["stats"].items():
            if lv != base.get(sk):
                changes.append(f"{sk} {base.get(sk)} -> {lv}")
        print("Since last check-in: " + (", ".join(changes) if changes else "no level changes"))
        prof["stats"].update(hs["stats"])
        for sk in prof.get("skill_xp", {}):
            if hs["xp"].get(sk) is not None:
                prof["skill_xp"][sk] = hs["xp"][sk]
        cap = (prof.get("build") or {}).get("skill_caps", {})
        for sk, c in cap.items():
            lv = hs["stats"].get(sk, 1)
            print(f"Build check: {sk} {lv}/{c}" + ("  ** CAP EXCEEDED **" if lv > c else ""))
        prof["snapshots"].append({"date": now_iso(), "stats": hs["stats"], "xp": hs["xp"]})
    since = (last or {}).get("date", prof.get("updated", today()))[:10]
    ups = new_updates(since)
    print(f"Game updates since {since}: " + (", ".join(u["title"].replace("Update:", "") for u in ups[:8]) or "none"))
    if ups:
        print("   -> if any touch your guides, run /osrs-refresh <job> (the Patch Sentinel decides relevance)")
    for line in where(prof):
        print(line)
    prof["updated"] = today()
    save_json(pf, prof)


def cmd_where(a):
    prof = load_json(PROFILES / f"{a.rsn}.json")
    for line in where(prof):
        print(line)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("today"); s.add_argument("rsn"); s.set_defaults(f=cmd_today)
    s = sp.add_parser("where"); s.add_argument("rsn"); s.set_defaults(f=cmd_where)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
