#!/usr/bin/env python3
"""Danger Score (DS) engine. The model is documented in docs/05-danger-model.md.

The Risk Officer *rates factors and cites evidence*. This file turns those
ratings into a score, so a score cannot be nudged by hand and two
assessments of the same ratings always agree.

  DS = min(100, round( 100 * T/5 * (0.35 + 0.13*C) * (0.80 + 0.04*E) + 2*K ))
     T = max(lethality, pvp)                                    threat
     C = max(escape, attention, disconnect, unpredictability)   loss of control
     E = exposure, K = knowledge gap
  then raised to the floor of any hazard flag that is present.

Residual DS applies each mitigation's factor reductions (at most 3 per
mitigation per factor) and keeps flags unless a mitigation removes them with
evidence. Residual can never drop below 30% of inherent when inherent >= 25
(no mitigation is perfect).

Commands
  score <job>            print inherent/residual DS for every risk entry
  explain                print the factor anchors, flags and tiers
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import job_dir, load_json  # noqa: E402

FACTORS = ["lethality", "pvp", "escape", "attention", "disconnect", "unpredictability", "exposure", "knowledge"]

ANCHORS = {
    "lethality": ["no damage source at all", "chip damage only; cannot threaten HP if you eat normally",
                  "steady damage, <=10% of your HP per hit", "hits up to ~25% HP, or stacking poison",
                  "hits up to ~50% HP, or multi-attacker burst", "a 1-2 tick sequence can exceed your current HP, or unavoidable/typeless damage"],
    "pvp": ["no PvP possible", "PvP world-hop risk only (e.g. passing through)", "low-level wilderness, single-combat, low traffic",
            "wilderness with regular traffic", "multi-combat wilderness or known PK route", "notorious PK hotspot"],
    "escape": ["walk away / teleport instantly", "short walk to safety", "teleport delayed or long exit path",
               "instance or cutscene with slow exit, or wilderness <=20", "wilderness 21-30 or no-teleport zone",
               "wilderness 30+, teleblock possible, or locked fight with no exit"],
    "attention": ["fully AFK-safe (nothing can hurt you)", "AFK-safe above an HP threshold", "periodic checks (every few minutes)",
                  "constant attention required", "prayer switching / mechanics to respect", "tick-precise mechanics"],
    "disconnect": ["a disconnect is harmless", "minor: you might take a hit", "aggressive NPCs nearby but low damage",
                   "you keep taking damage while logged in after a DC", "a DC mid-activity is likely to cost a lot of HP",
                   "a DC mid-activity is likely fatal"],
    "unpredictability": ["fully deterministic", "small known RNG", "RNG damage within known bounds",
                         "random spawns / aggression / interruptions", "high variance: venom, multi-attackers, stacking",
                         "poorly documented or brand-new mechanics"],
    "exposure": ["momentary", "under 5 minutes", "under 30 minutes", "a few hours", "tens of hours", "the bulk of a 100+ hour grind"],
    "knowledge": ["all facts verified by two independent T1 sources", "verified, minor caveats", "some single-source facts",
                  "disputed facts used", "content < 30 days old or thinly documented", "unverified facts used"],
}

FLAG_FLOORS = {
    "WILDERNESS": 45,
    "DEEP_WILDERNESS": 65,          # above level 20: normal teleports fail, teleblock reach
    "PVP_HOTSPOT": 75,
    "ONE_SHOT_POSSIBLE": 65,        # damage can exceed max HP in one tick
    "LOCKED_INSTANCE_LETHAL": 70,   # cannot leave a fight that can kill you
    "DISCONNECT_FATAL": 45,
    "UNVERIFIED_MECHANIC": 45,
    "NEW_CONTENT": 25,              # released < 30 days ago
    "HW_UNSAFE_ACTIVITY": 10,       # safe for HCIM, run-ending on Hardcore Worlds
    "POISON_OR_VENOM": 0,
    "AGGRESSIVE_NPCS_ON_ROUTE": 0,
    "LOW_HP_SKILLING_DAMAGE": 0,
    "TELEPORT_RESTRICTED": 0,
    "QUEST_BOSS": 0,
}

TIERS = [(0, "Safe"), (10, "Low"), (25, "Moderate"), (45, "High"), (65, "Severe"), (85, "Critical")]
APPETITE_CAPS = {"cautious": 24, "standard": 44, "bold": 64}


def tier(ds: int) -> str:
    name = TIERS[0][1]
    for lo, n in TIERS:
        if ds >= lo:
            name = n
    return name


def factor_values(factors: dict) -> dict[str, int]:
    vals = {}
    for f in FACTORS:
        v = factors.get(f, {})
        v = v.get("score") if isinstance(v, dict) else v
        if not isinstance(v, int) or not 0 <= v <= 5:
            raise ValueError(f"factor {f} must be an integer 0..5 (got {v!r})")
        vals[f] = v
    return vals


def raw_score(v: dict[str, int]) -> float:
    T = max(v["lethality"], v["pvp"])
    C = max(v["escape"], v["attention"], v["disconnect"], v["unpredictability"])
    E, K = v["exposure"], v["knowledge"]
    return 100 * (T / 5) * (0.35 + 0.13 * C) * (0.80 + 0.04 * E) + 2 * K


def apply_floors(score: float, flags: list[str]) -> tuple[int, str | None]:
    floor, why = 0, None
    for fl in flags:
        f = FLAG_FLOORS.get(fl)
        if f is None:
            raise ValueError(f"unknown hazard flag {fl}")
        if f > floor:
            floor, why = f, fl
    s = min(100, round(score))
    return (max(s, floor), why if floor > s else None)


def assess(entry: dict) -> dict:
    v = factor_values(entry["factors"])
    flags = list(entry.get("flags", []))
    inherent, floor_by = apply_floors(raw_score(v), flags)

    rv = dict(v)
    rflags = list(flags)
    for m in entry.get("mitigations", []):
        if m.get("mandatory", True) is False and not m.get("assume_applied", False):
            continue
        for f, delta in m.get("reduces", {}).items():
            if f not in FACTORS:
                raise ValueError(f"mitigation {m.get('id')} reduces unknown factor {f}")
            rv[f] = max(0, rv[f] - min(3, int(delta)))
        for fl in m.get("removes_flags", []):
            if fl in rflags and m.get("facts"):
                rflags.remove(fl)
    residual, rfloor_by = apply_floors(raw_score(rv), rflags)
    if inherent >= 25:
        residual = max(residual, math.ceil(0.3 * inherent))
    return {"step_id": entry["step_id"], "inherent_ds": inherent, "inherent_tier": tier(inherent),
            "residual_ds": residual, "residual_tier": tier(residual), "floor_by": floor_by,
            "residual_floor_by": rfloor_by, "factors": v, "residual_factors": rv,
            "flags": flags, "residual_flags": rflags}


def score_job(job: str) -> list[dict]:
    risk = load_json(job_dir(job) / "risk.json")
    return [assess(e) for e in risk["entries"]]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("score"); s.add_argument("job"); s.add_argument("--appetite", choices=list(APPETITE_CAPS))
    sp.add_parser("explain")
    a = p.parse_args()
    if a.cmd == "explain":
        print(json.dumps({"anchors": ANCHORS, "flag_floors": FLAG_FLOORS, "tiers": TIERS,
                          "appetite_caps": APPETITE_CAPS}, indent=2))
        return
    cap = APPETITE_CAPS.get(a.appetite) if a.appetite else None
    for r in score_job(a.job):
        over = f"  ABOVE {a.appetite.upper()} CAP {cap}" if cap is not None and r["residual_ds"] > cap else ""
        fl = f" floor:{r['floor_by']}" if r["floor_by"] else ""
        print(f"{r['step_id']:8s} inherent {r['inherent_ds']:3d} {r['inherent_tier']:9s} -> residual "
              f"{r['residual_ds']:3d} {r['residual_tier']:9s}{fl}{over}")


if __name__ == "__main__":
    main()
