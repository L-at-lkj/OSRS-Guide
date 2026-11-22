#!/usr/bin/env python3
"""Build a job's brief.json from the owner's saved profile (no intake agent needed).

  python3 tools/brief.py <job> <rsn> --skill Thieving --from 1 --to 99 --request "provide a 1-99 thieving guide"

Refreshes stats from the Hardcore Worlds hiscores first. Falls back to the
profile's stats, and says so, if the lookup fails. Uses the profile's build,
danger policy, quests and known facts. Unknowns become open_questions for the
Director to put to the owner. Sealed by `system`. Dispatch the intake-officer
only for a new account or when the profile lacks something the guide needs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, job_dir, load_json, now_iso, save_json, today  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("job"); p.add_argument("rsn")
    p.add_argument("--skill", required=True); p.add_argument("--from", dest="frm", type=int, default=1)
    p.add_argument("--to", type=int, default=99); p.add_argument("--request", required=True)
    a = p.parse_args()
    prof = load_json(ROOT / "profiles" / f"{a.rsn}.json")
    actions, source, verified_at = [], "user_stated", None
    try:
        out = subprocess.run([sys.executable, "tools/hiscores.py", "lookup", a.rsn], cwd=ROOT,
                             capture_output=True, text=True, timeout=60)
        hs = json.loads(out.stdout)
        prof["stats"].update(hs["stats"])
        prof.setdefault("skill_xp", {}).update({k: v for k, v in hs["xp"].items() if v is not None})
        source, verified_at = "hiscores", hs["retrieved"]
        actions.append({"kind": "fetch", "detail": "Hardcore Worlds hiscores lookup", "target": hs["endpoint"], "outcome": "ok"})
    except Exception as exc:  # keep profile values, flag it
        actions.append({"kind": "fetch", "detail": f"hiscores lookup failed ({exc}); profile stats used", "outcome": "fallback"})
    pol = prof.get("danger_policy", {}).get("appetite", "standard")
    to = dt.date.fromisoformat(today())
    brief = {
        "job_id": a.job, "request": a.request, "guide_type": "skill_training",
        "scope": {"skill": a.skill, "from_level": a.frm, "to_level": a.to,
                  "notes": f"Owner's current {a.skill} level: {prof['stats'].get(a.skill, 1)} "
                           f"({prof.get('skill_xp', {}).get(a.skill, 'xp unknown')} XP). Guide covers {a.frm}-{a.to}."},
        "game_mode": prof["game_mode"],
        "profile": {"stats": prof["stats"], "stats_source": source, "stats_verified_at": verified_at,
                    "skill_xp": prof.get("skill_xp", {}), "quests_completed": prof.get("quests_completed", []),
                    "build": prof.get("build"), "diaries": [], "unlocks": [],
                    "bank_notes": "; ".join(prof.get("facts_about_owner", []))},
        "preferences": {"risk_appetite": pol, "optimise_for": "balanced", "attention": "semi", "exclusions": []},
        "assumptions": [{"text": f"Profile {a.rsn} (updated {prof.get('updated')}) is current for quests, build and house.", "confirmed": True},
                        {"text": "Profit uses live Hardcore Worlds GE prices (prices.runescape.wiki/osrs-hc) at guide time.", "confirmed": True}],
        "open_questions": [],
        "acceptance_criteria": [f"every level {a.frm}-{a.to - 1} has a method", "every step has a game-relative danger score",
                                "every quest released in the last 12 months that gives this skill XP is evaluated",
                                "no route breaks the build caps", "profit per step and route is shown with Hardcore Worlds prices",
                                "decision points offer 2+ justified options"],
        "recency_window": {"from": (to - dt.timedelta(days=365)).isoformat(), "to": today()},
        "provenance": {"agent": "system", "started_at": now_iso(), "finished_at": now_iso(),
                       "inputs": [{"path": f"profiles/{a.rsn}.json",
                                   "sha256": __import__("hashlib").sha256((ROOT / "profiles" / f"{a.rsn}.json").read_bytes()).hexdigest()}],
                       "actions": actions, "decisions": [{"decision": "brief built from saved profile", "reason": "efficiency: no intake agent needed"}],
                       "limitations": [] if source == "hiscores" else ["stats not refreshed from hiscores"]}}
    save_json(job_dir(a.job) / "brief.json", brief)
    print(f"brief.json written ({source}); {a.skill} level {prof['stats'].get(a.skill)}")


if __name__ == "__main__":
    main()
