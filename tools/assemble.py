#!/usr/bin/env python3
"""Deterministically assemble content.json from sealed, validated artifacts.

No agent writes the final guide content by hand. This script merges:
brief + updates + facts + plan + calc + risk (scores recomputed by danger.py)
+ red-team + prose, and records the hash of every input it used.

  python3 tools/assemble.py <job>
Refuses to run if any input is unsealed or differs from its seal.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import die, job_dir, load_json, now_iso, save_json, sha256_file  # noqa: E402
import danger  # noqa: E402
import ledger  # noqa: E402

INPUTS = ["brief.json", "research/updates.json", "facts.json", "plan.json", "calc.json", "calc-review.json",
          "risk.json", "redteam.json", "prose.json"]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("job")
    a = p.parse_args()
    d = job_dir(a.job)
    state = ledger.seal_state(ledger.read_entries(a.job))
    for rel in INPUTS:
        st = state.get(rel)
        if not st or not st["sealed"]:
            die(f"{rel} is not sealed; assemble only uses sealed artifacts")
        if sha256_file(d / rel) != st["sha256"]:
            die(f"{rel} differs from its seal")

    brief, updates, facts, plan, calc, risk, redteam, prose = (
        load_json(d / r) for r in ("brief.json", "research/updates.json", "facts.json", "plan.json",
                                   "calc.json", "risk.json", "redteam.json", "prose.json"))
    fidx = {f["fact_id"]: f for f in facts["facts"]}
    pidx = {s["step_id"]: s for s in prose["steps"]}
    ridx = {e["step_id"]: e for e in risk["entries"]}
    cap = danger.APPETITE_CAPS[risk["risk_appetite"]]
    lad = danger.ladder()

    used = set()
    steps = []
    for st in plan["steps"]:
        used.update(st["facts"])
        for k in ("xp_per_action", "xp_per_hour", "est_hours"):
            if isinstance(st.get(k), dict):
                used.add(st[k]["fact"])
        for req in st.get("requirements", []):
            used.add(req["fact"])
        re_ = ridx[st["step_id"]]
        for fac in re_["factors"].values():
            used.update(fac.get("facts", []))
        for m in re_["mitigations"]:
            used.update(m.get("facts", []))
        used.update(re_["hw_death_classification"].get("facts", []))
        steps.append({**st, "prose": pidx.get(st["step_id"]), "risk": {**re_, "score": danger.assess(re_, lad)}})

    routes = []
    for rt in plan["routes"]:
        c = calc["routes"][rt["route_id"]]
        worst = max((danger.assess(ridx[s])["residual_ds"] for s in rt["step_ids"]), default=0)
        # Q-10: per-level labels always come from the sealed plan, never from calc's copy
        pidx_steps = {st["step_id"]: st for st in plan["steps"]}
        levels = [{**L, "method": pidx_steps[L["step_id"]].get("method") or pidx_steps[L["step_id"]]["title"]}
                  for L in c["levels"]]
        routes.append({**rt, "totals": c["totals"], "levels": levels,
                       "calc": {s["step_id"]: s for s in c["steps"]},
                       "worst_residual_ds": worst, "worst_residual_tier": danger.tier(worst),
                       "steps_over_cap": [s for s in rt["step_ids"] if danger.assess(ridx[s])["residual_ds"] > cap]})

    step_hours = {}
    for rt in routes:
        for sid, c in rt["calc"].items():
            step_hours.setdefault(sid, c.get("hours", 0))
    dps = []
    for dp in plan.get("decision_points", []):
        opts = []
        for o in dp["options"]:
            worst = max(danger.assess(ridx[s])["residual_ds"] for s in o["step_ids"])
            used.update(o.get("facts", []))
            opts.append({**o, "worst_residual_ds": worst, "worst_residual_tier": danger.tier(worst),
                         "hours": round(sum(step_hours.get(s, 0) or 0 for s in o["step_ids"]), 2),
                         "over_cap": worst > cap})
        dps.append({**dp, "options": opts})
    upd_items = [it for it in updates["items"] if it["relevance"] != "none"]
    content = {
        "schema": "osrs-guide-content/1",
        "job": a.job,
        "assembled_at": now_iso(),
        "inputs": {rel: sha256_file(d / rel) for rel in INPUTS},
        "meta": {
            "title": prose["title"], "subtitle": prose.get("subtitle", ""),
            "skill": plan["target"]["skill"], "from_level": plan["target"]["from_level"],
            "to_level": plan["target"]["to_level"], "facts_as_of": facts["as_of"],
            "updates_as_of": updates["as_of"], "recency_window": brief["recency_window"],
            "game_mode": brief["game_mode"], "profile": brief["profile"], "preferences": brief["preferences"],
            "risk_appetite": risk["risk_appetite"], "risk_cap": cap,
        },
        "intro": prose["intro"], "outro": prose.get("outro", ""),
        "routes": routes,
        "steps": steps,
        "decision_points": dps,
        "capped_skills": {rid: calc["routes"][rid].get("capped_skills", {}) for rid in calc["routes"]},
        "facts": [fidx[f] for f in sorted(used) if f in fidx],
        "updates": upd_items,
        "upcoming": updates.get("upcoming_30d", []),
        "redteam": redteam["findings"],
        "risk_rules": risk.get("general_rules", []),
        "assumptions": plan["assumptions"] + [x["text"] for x in brief.get("assumptions", [])],
        "danger_model": {"tiers": danger.TIERS, "caps": danger.APPETITE_CAPS, "flags": danger.FLAG_FLOORS,
                         "anchors": danger.ANCHORS, "factors": danger.FACTORS, "prep_card_from": danger.PREP_CARD_FROM,
                         "ladder": {k: lad[k] for k in ("calibrated", "version", "anchors", "conflicts")},
                         "wilderness_premium": (danger.load_calibration() or {}).get("wilderness_premium"),
                         "ladder_proposed": [{"activity": a["activity"], "position": a["position"], "status": a["status"]}
                                             for a in (danger.load_calibration() or {}).get("anchors", [])]},
    }
    save_json(d / "content.json", content)
    print(f"content.json assembled: {len(steps)} steps, {len(routes)} routes, {len(content['facts'])} facts")


if __name__ == "__main__":
    main()
