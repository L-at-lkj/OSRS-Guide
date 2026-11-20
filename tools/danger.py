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

GAME-RELATIVE CALIBRATION (Gielinor Danger Index)
  The model score above ("raw model DS") is then placed on a ladder of
  reference activities from across the whole game (policy/danger-calibration.json).
  The most dangerous content in the game (The Fractured Archive, hardest mode)
  is pinned at 100. Each rated anchor contributes a point (its raw model DS ->
  its board-approved position); the mapping between points is monotone
  piecewise-linear. A step's published score is therefore "how dangerous this
  is for YOU, on a scale where the hardest content in the game is 100", plus
  the nearest reference activities. Until enough anchors are rated
  (MIN_ANCHORS, including the top anchor), scores are published uncalibrated
  and labelled as such.

Commands
  score <job>            print raw and game-relative scores for every risk entry
  explain                print the factor anchors, flags, tiers and calibration
  ladder                 print the calibration ladder (anchor raw -> position)
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

TIERS = [(0, "Safe"), (10, "Low"), (25, "Moderate"), (45, "High"), (65, "Severe"), (85, "Extreme")]
# informed = awareness only: no cap gates content; high-danger steps must carry a full prep card instead.
APPETITE_CAPS = {"cautious": 24, "standard": 44, "bold": 64, "informed": 100}
PREP_CARD_FROM = 45   # game-relative score from which a complete prep card is mandatory
MIN_ANCHORS = 6
CALIBRATION = Path(__file__).resolve().parent.parent / "policy" / "danger-calibration.json"


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


def load_calibration() -> dict | None:
    if not CALIBRATION.exists():
        return None
    return json.loads(CALIBRATION.read_text(encoding="utf-8"))


def ladder(cal: dict | None = None) -> dict:
    """Rated anchors -> monotone (raw, position) points. Reports ordering conflicts."""
    cal = cal if cal is not None else load_calibration()
    out = {"calibrated": False, "points": [], "conflicts": [], "anchors": [], "version": None}
    if not cal:
        return out
    out["version"] = cal.get("version")
    rated = []
    for a in cal.get("anchors", []):
        if a.get("status") not in ("rated", "approved") or "factors" not in a:
            continue
        raw, _ = apply_floors(raw_score(factor_values(a["factors"])), a.get("flags", []))
        prem = premium(a.get("flags", []), cal, a.get("wilderness_level"))
        rated.append({"id": a["id"], "activity": a["activity"], "position": a["position"], "raw": raw,
                      "published": min(int((cal.get("wilderness_premium") or {}).get("cap", 99)), a["position"] + prem)
                      if prem else a["position"], "premium": prem})
    rated.sort(key=lambda x: (x["position"], x["raw"]))
    for lo, hi in zip(rated, rated[1:]):
        if hi["raw"] < lo["raw"]:
            out["conflicts"].append(f"{hi['activity']} (pos {hi['position']}, raw {hi['raw']}) rates below "
                                    f"{lo['activity']} (pos {lo['position']}, raw {lo['raw']})")
    # Isotonic (pool-adjacent-violators) fit of board position on model raw score: the
    # monotone mapping closest to the board's judgement. Where the model cannot separate
    # anchors (e.g. several instanced bosses at raw 94), they share their averaged position.
    by_raw = sorted(rated, key=lambda x: (x["raw"], x["position"]))
    blocks = []  # [sum_pos, count, max_raw, min_raw]
    for a in by_raw:
        blocks.append([a["position"], 1, a["raw"], a["raw"]])
        while len(blocks) > 1 and (blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]
                                   or blocks[-2][2] == blocks[-1][3]):
            b = blocks.pop()
            blocks[-1][0] += b[0]; blocks[-1][1] += b[1]; blocks[-1][2] = b[2]
    pts = [(0, 0)]
    for sm, n, rmax, rmin in blocks:
        pos = round(sm / n, 1)
        if rmin == rmax:
            pts.append((rmax, pos))
        else:
            pts.append((rmin, pos)); pts.append((rmax, pos))
    top = max(rated, key=lambda a: a["position"]) if rated else None
    if top and top["position"] == 100:
        pts.append((101, 100))
    out["points"] = pts
    out["anchors"] = rated
    top = [a for a in cal.get("anchors", []) if a.get("position") == 100 and a.get("status") in ("rated", "approved")]
    out["calibrated"] = len(rated) >= MIN_ANCHORS and bool(top)
    return out


def premium(flags: list[str], cal: dict | None = None, level: int | None = None) -> int:
    """Owner-set tiered Wilderness premium (policy wilderness_premium), added after calibration.
    The tier comes from the deepest Wilderness level of the activity (`wilderness_level`); when
    that is missing, the most severe flag present implies a level (flag_fallback)."""
    cal = cal if cal is not None else load_calibration()
    wp = (cal or {}).get("wilderness_premium")
    if not wp or not any(f in wp["flags"] for f in flags):
        return 0
    if "tiers" not in wp:  # legacy flat premium
        return int(wp.get("points", 0))
    if level is None:
        level = max(wp.get("flag_fallback", {}).get(f, 0) for f in flags if f in wp["flags"])
    for threshold, pts in wp["tiers"]:
        if level >= threshold:
            return int(pts)
    return 0


def calibrate(raw: int, lad: dict) -> tuple[int, list[str]]:
    """Map a raw model DS onto the game-relative ladder; returns (score, nearest anchors)."""
    if not lad["calibrated"]:
        return raw, []
    pts = lad["points"]
    if raw >= pts[-1][0]:
        return min(100, round(pts[-1][1])), [lad["anchors"][-1]["activity"]]
    for (r0, p0), (r1, p1) in zip(pts, pts[1:]):
        if r0 <= raw <= r1:
            pos = p0 if r1 == r0 else p0 + (p1 - p0) * (raw - r0) / (r1 - r0)
            near = sorted(lad["anchors"], key=lambda a: (abs(a["raw"] - raw), -a["position"]))[:2]
            return round(pos), [a["activity"] for a in near]
    return raw, []


def assess(entry: dict, lad: dict | None = None) -> dict:
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
    lad = lad if lad is not None else ladder()
    g_inh, _ = calibrate(inherent, lad)
    g_res, near = calibrate(residual, lad)
    cal = load_calibration()
    cap = int(((cal or {}).get("wilderness_premium") or {}).get("cap", 99))
    wl = entry.get("wilderness_level")
    p_inh, p_res = premium(flags, cal, wl), premium(rflags, cal, wl)
    if lad["calibrated"] and (p_inh or p_res):
        g_inh = min(cap, g_inh + p_inh) if p_inh else g_inh
        g_res = min(cap, g_res + p_res) if p_res else g_res
    return {"step_id": entry["step_id"],
            # published (game-relative) scores
            "inherent_ds": g_inh, "inherent_tier": tier(g_inh), "residual_ds": g_res, "residual_tier": tier(g_res),
            "comparable_to": near, "calibrated": lad["calibrated"], "calibration_version": lad.get("version"),
            "wilderness_premium": p_res if lad["calibrated"] else 0,
            # model internals, kept for audit
            "model_inherent": inherent, "model_residual": residual,
            "floor_by": floor_by, "residual_floor_by": rfloor_by, "factors": v, "residual_factors": rv,
            "flags": flags, "residual_flags": rflags, "necessity": entry.get("necessity")}


def score_job(job: str) -> list[dict]:
    risk = load_json(job_dir(job) / "risk.json")
    lad = ladder()
    return [assess(e, lad) for e in risk["entries"]]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("score"); s.add_argument("job"); s.add_argument("--appetite", choices=list(APPETITE_CAPS))
    sp.add_parser("explain")
    sp.add_parser("ladder")
    a = p.parse_args()
    if a.cmd == "explain":
        lad = ladder()
        print(json.dumps({"anchors": ANCHORS, "flag_floors": FLAG_FLOORS, "tiers": TIERS,
                          "appetite_caps": APPETITE_CAPS, "prep_card_from": PREP_CARD_FROM,
                          "calibrated": lad["calibrated"], "calibration_version": lad["version"]}, indent=2))
        return
    if a.cmd == "ladder":
        lad = ladder()
        print(f"calibration {lad['version']}: {'CALIBRATED' if lad['calibrated'] else 'NOT CALIBRATED (scores published raw)'}")
        for an in lad["anchors"]:
            extra = f"  (+{an['premium']} Wilderness -> {an['published']})" if an.get("premium") else ""
            print(f"  pos {an['position']:3d}  raw {an['raw']:3d}  {an['activity']}{extra}")
        for c in lad["conflicts"]:
            print("  CONFLICT " + c)
        return
    cap = APPETITE_CAPS.get(a.appetite) if a.appetite else None
    for r in score_job(a.job):
        over = f"  ABOVE {a.appetite.upper()} CAP {cap}" if cap is not None and r["residual_ds"] > cap else ""
        fl = f" floor:{r['floor_by']}" if r["floor_by"] else ""
        near = f"  ~ {', '.join(r['comparable_to'])}" if r["comparable_to"] else ""
        print(f"{r['step_id']:8s} raw {r['inherent_ds']:3d} {r['inherent_tier']:9s} -> residual "
              f"{r['residual_ds']:3d} {r['residual_tier']:9s}{fl}{over}{near}"
              f"{'' if r['calibrated'] else '  [uncalibrated]'}")


if __name__ == "__main__":
    main()
