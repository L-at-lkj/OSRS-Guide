#!/usr/bin/env python3
"""Deterministic experience calculator (the Quant's instrument).

No language model does arithmetic in this company: every XP figure, action
count, time estimate and supply total in a guide comes from this file.

Commands
  table [--max 126]                  print the XP table as JSON
  level <xp>                         level for an XP amount
  xp <level>                         XP needed for a level
  simulate <job> [--out calc.json]   walk every route in plan.json and write calc.json

Simulation rules
  * Steps run in the order each route lists them, starting from plan.start_xp.
  * train   : trains the target skill from the current XP up to `until_level`.
  * quest / unlock / reward : adds `xp_rewards` and chosen `lamp_rewards` for the target skill.
  * Every step's `min_level` and every target-skill requirement is checked
    against the *simulated* level at that point. A violation is an error.
  * Levels reached through quest rewards are recorded with zero actions.
  * Build caps (brief.profile.build.skill_caps, e.g. a zerker's Defence 45) are
    enforced: XP from quest rewards, lamps and secondary XP into a capped skill
    is tracked per route, and exceeding the cap (or any lamp put into a
    capped skill) is an error.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import die, job_dir, load_json, save_json, sha256_file  # noqa: E402

MAX_LEVEL = 126  # virtual levels; 99 is the cap for real levels
MAX_XP = 200_000_000


def build_table(max_level: int = MAX_LEVEL) -> list[int]:
    """XP[L] = total XP needed for level L (index 0 unused, XP[1] = 0)."""
    table = [0, 0]
    points = 0
    for lvl in range(1, max_level):
        points += math.floor(lvl + 300 * 2 ** (lvl / 7))
        table.append(points // 4)
    return table


XP_TABLE = build_table()
assert XP_TABLE[2] == 83 and XP_TABLE[99] == 13_034_431, "XP table self-check failed"


def xp_for(level: int) -> int:
    return XP_TABLE[max(1, min(level, MAX_LEVEL))]


def level_for(xp: float) -> int:
    lvl = 1
    for L in range(2, 100):
        if xp >= XP_TABLE[L]:
            lvl = L
        else:
            break
    return lvl


def _num(v):
    """Plan fields hold {'value': n, 'fact': id}; accept bare numbers defensively."""
    if isinstance(v, dict):
        return v.get("value")
    return v


def simulate_route(plan: dict, route: dict, brief: dict | None = None) -> dict:
    skill = plan["target"]["skill"]
    profile = (brief or {}).get("profile", {})
    caps = (profile.get("build") or {}).get("skill_caps", {})
    capped_xp = {sk: float(xp_for(profile.get("stats", {}).get(sk, 1) or 1)) for sk in caps}
    cap_log: list[dict] = []
    steps_by_id = {s["step_id"]: s for s in plan["steps"]}
    xp = float(plan.get("start_xp", xp_for(plan["target"].get("from_level", 1))))
    cum_hours = 0.0
    out_steps, levels, errors, warnings = [], [], [], []
    supplies_total: dict[str, float] = {}
    secondary_total: dict[str, float] = {}
    level_rows: dict[int, dict] = {}

    for sid in route["step_ids"]:
        step = steps_by_id.get(sid)
        if step is None:
            errors.append(f"route {route['route_id']}: unknown step {sid}")
            continue
        start_xp, start_level = xp, level_for(xp)
        min_level = step.get("min_level", 1)
        if start_level < min_level:
            errors.append(f"{sid}: needs {skill} {min_level} but simulated level is {start_level}")
        for req in step.get("requirements", []):
            if req.get("type") == "skill" and req.get("skill") == skill and start_level < req.get("level", 1):
                errors.append(f"{sid}: requirement {skill} {req['level']} not met (level {start_level})")
        rec = {"step_id": sid, "kind": step["kind"], "start_xp": round(start_xp), "start_level": start_level,
               "actions": 0, "hours": 0.0, "supplies": [], "secondary_xp": []}

        if step["kind"] == "train":
            target = step.get("until_level")
            xpa, xph = _num(step.get("xp_per_action")), _num(step.get("xp_per_hour"))
            if not target or not xpa or not xph:
                errors.append(f"{sid}: train step needs until_level, xp_per_action and xp_per_hour")
                continue
            goal_xp = xp_for(target)
            if xp >= goal_xp:
                warnings.append(f"{sid}: already level {start_level} >= {target}; step is redundant on this route")
            else:
                # per-level rows for every level crossed in this step
                for L in range(start_level, target):
                    seg_start = max(xp, xp_for(L))
                    seg_xp = xp_for(L + 1) - seg_start
                    seg_hours = seg_xp / xph
                    level_rows[L] = {"level": L, "xp": xp_for(L), "xp_to_next": xp_for(L + 1) - xp_for(L),
                                     "step_id": sid, "method": step.get("method", step.get("title", "")),
                                     "actions_to_next": math.ceil(seg_xp / xpa),
                                     "hours_to_next": round(seg_hours, 3),
                                     "cum_hours_at_next": round(cum_hours + (xp_for(L + 1) - start_xp) / xph, 3)}
                gained = goal_xp - xp
                actions = math.ceil(gained / xpa)
                gained_actual = actions * xpa  # whole actions overshoot slightly
                hours = gained / xph
                xp += gained_actual
                cum_hours += hours
                rec.update(actions=actions, hours=round(hours, 3))
                for sup in step.get("supplies_per_action", []):
                    qty = math.ceil(_num(sup.get("qty", 0)) * actions)
                    rec["supplies"].append({"item": sup["item"], "qty": qty})
                    supplies_total[sup["item"]] = supplies_total.get(sup["item"], 0) + qty
                for sec in step.get("secondary_xp_per_action", []):
                    sxp = round(_num(sec["xp"]) * actions)
                    rec["secondary_xp"].append({"skill": sec["skill"], "xp": sxp})
                    secondary_total[sec["skill"]] = secondary_total.get(sec["skill"], 0) + sxp
                    if sec["skill"] in capped_xp:
                        capped_xp[sec["skill"]] += sxp
                        cap_log.append({"step_id": sid, "skill": sec["skill"], "xp": sxp,
                                        "total_xp": capped_xp[sec["skill"]], "level": level_for(capped_xp[sec["skill"]])})
        else:
            gained = 0.0
            for r in step.get("xp_rewards", []):
                if r["skill"] == skill:
                    gained += _num(r["xp"])
                else:
                    secondary_total[r["skill"]] = secondary_total.get(r["skill"], 0) + _num(r["xp"])
                    if r["skill"] in capped_xp:
                        capped_xp[r["skill"]] += _num(r["xp"])
                        cap_log.append({"step_id": sid, "skill": r["skill"], "xp": _num(r["xp"]),
                                        "total_xp": capped_xp[r["skill"]], "level": level_for(capped_xp[r["skill"]])})
            for lamp in step.get("lamp_rewards", []):
                if lamp.get("chosen_skill") in caps:
                    errors.append(f"{sid}: lamp put into capped skill {lamp['chosen_skill']} (build policy forbids it)")
                if lamp.get("chosen_skill") != skill:
                    continue
                for _ in range(lamp.get("count", 1)):
                    if "xp" in lamp:
                        gained += _num(lamp["xp"])
                    elif "xp_per_level" in lamp:  # e.g. lamps worth level x N
                        gained += _num(lamp["xp_per_level"]) * level_for(xp + gained)
            before = level_for(xp)
            xp = min(MAX_XP, xp + gained)
            for L in range(before, level_for(xp)):
                level_rows[L] = {"level": L, "xp": xp_for(L), "xp_to_next": xp_for(L + 1) - xp_for(L),
                                 "step_id": sid, "method": step.get("title", sid), "actions_to_next": 0,
                                 "hours_to_next": 0.0, "cum_hours_at_next": round(cum_hours, 3)}
            hrs = _num(step.get("est_hours", 0)) or 0
            cum_hours += hrs
            rec["hours"] = hrs

        for sk, cap in caps.items():
            if level_for(capped_xp[sk]) > cap:
                errors.append(f"{sid}: pushes {sk} to level {level_for(capped_xp[sk])}, above the build cap {cap}")
        rec.update(end_xp=round(xp), end_level=level_for(xp), xp_gained=round(xp - start_xp),
                   cum_hours=round(cum_hours, 3))
        out_steps.append(rec)

    goal = plan["target"].get("to_level", 99)
    if level_for(xp) < goal:
        errors.append(f"route {route['route_id']} ends at level {level_for(xp)}, short of {goal}")
    start_level = level_for(float(plan.get("start_xp", 0)))
    missing = [L for L in range(start_level, min(goal, 99)) if L not in level_rows]
    if missing:
        errors.append(f"route {route['route_id']}: no step covers level(s) {missing[:10]}{'...' if len(missing) > 10 else ''}")
    levels = [level_rows[L] for L in sorted(level_rows)]
    capped = {sk: {"cap": cap, "end_xp": round(capped_xp[sk]), "end_level": level_for(capped_xp[sk]),
                   "headroom_xp": xp_for(cap + 1) - 1 - round(capped_xp[sk]), "events": [e for e in cap_log if e["skill"] == sk]}
              for sk, cap in caps.items()}
    return {"steps": out_steps, "levels": levels, "errors": errors, "warnings": warnings, "capped_skills": capped,
            "totals": {"xp_end": round(xp), "level_end": level_for(xp), "hours": round(cum_hours, 2),
                       "actions": sum(s["actions"] for s in out_steps),
                       "supplies": [{"item": k, "qty": v} for k, v in sorted(supplies_total.items())],
                       "secondary_xp": [{"skill": k, "xp": v} for k, v in sorted(secondary_total.items())]}}


def cmd_simulate(a):
    d = job_dir(a.job)
    plan_path = d / "plan.json"
    plan = load_json(plan_path)
    brief = load_json(d / "brief.json") if (d / "brief.json").exists() else None
    result = {"generated_by": "tools/xp.py", "plan_sha256": sha256_file(plan_path),
              "skill": plan["target"]["skill"], "routes": {}}
    n_err = 0
    for route in plan["routes"]:
        r = simulate_route(plan, route, brief)
        result["routes"][route["route_id"]] = r
        n_err += len(r["errors"])
        status = "OK" if not r["errors"] else f"{len(r['errors'])} error(s)"
        print(f"route {route['route_id']:10s} -> level {r['totals']['level_end']}, "
              f"{r['totals']['hours']} h, {r['totals']['actions']} actions: {status}")
        for e in r["errors"]:
            print(f"   ERROR {e}")
        for w in r["warnings"]:
            print(f"   warn  {w}")
    save_json(d / (a.out or "calc.json"), result)
    sys.exit(1 if n_err else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("table"); s.add_argument("--max", type=int, default=99)
    s = sp.add_parser("level"); s.add_argument("xp", type=float)
    s = sp.add_parser("xp"); s.add_argument("level", type=int)
    s = sp.add_parser("simulate"); s.add_argument("job"); s.add_argument("--out")
    a = p.parse_args()
    if a.cmd == "table":
        print(json.dumps({L: XP_TABLE[L] for L in range(1, a.max + 1)}))
    elif a.cmd == "level":
        print(level_for(a.xp))
    elif a.cmd == "xp":
        if not 1 <= a.level <= MAX_LEVEL:
            die("level must be 1..126")
        print(xp_for(a.level))
    else:
        cmd_simulate(a)


if __name__ == "__main__":
    main()
