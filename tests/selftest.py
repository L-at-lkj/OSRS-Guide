#!/usr/bin/env python3
"""Self-test: runs a SYNTHETIC job through every tool and gate in a throwaway
copy of the project, then attacks the controls (tampering, out-of-scope
writes, shell tricks, forged dispatches) and checks they are caught.

  python3 tests/selftest.py            (from the project root)

The fixture uses a made-up skill ("Fixture") so nobody mistakes it for advice.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="osrs-selftest-"))
for d in ("tools", "schemas", "templates"):
    shutil.copytree(SRC / d, TMP / d)
(TMP / "jobs").mkdir()
ENV = {**os.environ, "CLAUDE_PROJECT_DIR": str(TMP)}
ENV.pop("OSRS_GOVERNANCE_MODE", None)
JOB = "fixture-1-20-selftest"
J = TMP / "jobs" / JOB
fails = 0


def run(*args, expect=0, stdin=None, env=None):
    global fails
    r = subprocess.run(args, cwd=TMP, env=env or ENV, input=stdin, capture_output=True, text=True)
    ok = (r.returncode == expect) if expect is not None else True
    tag = "PASS" if ok else "FAIL"
    if not ok:
        fails += 1
    print(f"{tag} [{r.returncode}] {' '.join(str(a) for a in args)[:110]}")
    if not ok:
        print("      " + (r.stdout + r.stderr).strip().replace("\n", "\n      ")[:1500])
    return r


def write(rel, obj):
    p = J / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2) if not isinstance(obj, str) else obj)


def sha(rel):
    import hashlib
    return hashlib.sha256((J / rel).read_bytes()).hexdigest()


def prov(agent, inputs=()):
    return {"agent": agent, "started_at": "2026-11-19T00:00:00Z", "finished_at": "2026-11-19T00:10:00Z",
            "inputs": [{"path": p, "sha256": sha(p)} for p in inputs],
            "actions": [{"kind": "read", "detail": "synthetic fixture"}],
            "decisions": [{"decision": "fixture", "reason": "self-test"}], "limitations": ["synthetic data"]}


SRCW = {"tier": "T2", "title": "Fixture page", "url": "https://oldschool.runescape.wiki/w/index.php?oldid=1", "revid": 1,
        "retrieved": "2026-11-19", "quote": "fixture"}
SRCV = {**SRCW, "retrieved": "2099-01-01"}  # verifier fetched after the research seal


def claim(cid, subject, attr, value, unit=None):
    return {"claim_id": cid, "subject": subject, "attribute": attr, "value": value, "unit": unit,
            "statement": f"{subject} {attr} is {value}", "sources": [SRCW], "confidence": "high"}


def main():
    py = sys.executable
    run(py, "tools/xp.py", "xp", "99")
    run(py, "tools/ledger.py", "init", JOB, "--request", "Fixture 1-20 self-test")

    write("brief.json", {"job_id": JOB, "request": "Fixture 1-20", "guide_type": "skill_training",
        "scope": {"skill": "Fixture", "from_level": 1, "to_level": 20},
        "game_mode": {"world_type": "hardcore_worlds", "account_type": "standard", "membership": "member", "death_ruleset": "hardcore_worlds"},
        "profile": {"stats": {"Hitpoints": 10, "Defence": 1}, "stats_source": "assumed_minimum", "quests_completed": [],
                    "build": {"archetype": "fixture-zerker", "skill_caps": {"Defence": 3}, "xp_rules": ["Defence only from quests"],
                              "lamp_policy": "never Defence", "confirmed": True}},
        "preferences": {"risk_appetite": "standard", "optimise_for": "balanced"},
        "assumptions": [], "open_questions": [], "acceptance_criteria": ["a", "b", "c"],
        "recency_window": {"from": "2025-11-19", "to": "2026-11-19"}, "provenance": prov("intake-officer")})
    run(py, "tools/validate.py", JOB, "brief")
    run(py, "tools/ledger.py", "seal", JOB, "brief.json", "--author", "intake-officer")
    run(py, "tools/ledger.py", "seal", JOB, "brief.json", "--author", "intake-officer", expect=1)  # double seal refused
    run(py, "tools/ledger.py", "seal", JOB, "brief.json", "--author", "guide-author", expect=1)  # wrong role refused (already sealed too)

    upd_claim = claim("C-UPD-001", "Fixture quest", "release_date", "2026-11-11")
    write("research/updates.json", {"desk": "updates", "as_of": "2026-11-19", "window": {"from": "2025-11-19", "to": "2026-11-19"},
        "sources_swept": [{"name": "wiki", "url": "https://oldschool.runescape.wiki", "retrieved": "2026-11-19"},
                          {"name": "news", "url": "https://secure.runescape.com/m=news", "retrieved": "2026-11-19"}],
        "items": [{"update_id": "U-001", "date": "2026-11-11", "title": "Fixture quest released", "kinds": ["new_quest"],
                   "relevance": "high", "summary": "Adds fixture XP", "claim_ids": ["C-UPD-001"]}],
        "claims": [upd_claim], "gaps": [], "provenance": prov("patch-sentinel", ["brief.json"])})
    mth = [claim("C-MTH-001", "Fixture rock", "xp_per_action", 10), claim("C-MTH-002", "Fixture rock", "xp_per_hour", 5000),
           claim("C-MTH-003", "Fixture tree", "xp_per_action", 25), claim("C-MTH-004", "Fixture tree", "xp_per_hour", 12000),
           claim("C-MTH-005", "Fixture tree", "level_requirement", 8)]
    write("research/claims-methods.json", {"desk": "methods", "as_of": "2026-11-19", "claims": mth, "gaps": [], "provenance": prov("methods-analyst", ["brief.json"])})
    write("research/claims-quests.json", {"desk": "quests", "as_of": "2026-11-19", "claims": [claim("C-QST-001", "Fixture quest", "xp_reward", 500),
                                                                                            claim("C-QST-002", "Fixture quest", "defence_xp_reward", 150)], "gaps": [], "provenance": prov("quest-archivist", ["brief.json"])})
    write("research/claims-threats.json", {"desk": "threats", "as_of": "2026-11-19", "claims": [claim("C-THR-001", "Fixture tree", "failure_damage_max", 2)], "gaps": [], "provenance": prov("threat-analyst", ["brief.json"])})
    write("research/claims-logistics.json", {"desk": "logistics", "as_of": "2026-11-19", "claims": [claim("C-LOG-001", "Fixture tree", "logs_per_action", 1)], "gaps": [], "provenance": prov("logistics-analyst", ["brief.json"])})
    run(py, "tools/validate.py", JOB, "research")
    for rel, who in [("research/updates.json", "patch-sentinel"), ("research/claims-methods.json", "methods-analyst"),
                     ("research/claims-quests.json", "quest-archivist"), ("research/claims-threats.json", "threat-analyst"),
                     ("research/claims-logistics.json", "logistics-analyst")]:
        run(py, "tools/ledger.py", "seal", JOB, rel, "--author", who)

    allc = mth + [upd_claim, claim("C-QST-001", "Fixture quest", "xp_reward", 500), claim("C-QST-002", "Fixture quest", "defence_xp_reward", 150), claim("C-THR-001", "Fixture tree", "failure_damage_max", 2),
                  claim("C-LOG-001", "Fixture tree", "logs_per_action", 1)]
    facts = []
    for i, c in enumerate(allc, 1):
        facts.append({"fact_id": f"F-{i:04d}", "claim_id": c["claim_id"], "subject": c["subject"], "attribute": c["attribute"],
                      "value": c["value"], "unit": None, "statement": c["statement"], "status": "VERIFIED",
                      "sources": [SRCV], "verified_at": "2026-11-19", "independent": True})
    fx = {f["claim_id"]: f["fact_id"] for f in facts}
    write("facts.json", {"as_of": "2026-11-19", "facts": facts, "rfi": [], "provenance": prov("fact-verifier", [
        "research/updates.json", "research/claims-methods.json"])})
    run(py, "tools/validate.py", JOB, "facts")
    run(py, "tools/ledger.py", "seal", JOB, "facts.json", "--author", "fact-verifier")

    F = lambda cid, v: {"value": v, "fact": fx[cid]}
    plan = {"target": {"skill": "Fixture", "from_level": 1, "to_level": 20}, "start_xp": 0,
        "routes": [{"route_id": "safest", "label": "Safest", "intent": "no damage", "step_ids": ["S01", "S02"]},
                   {"route_id": "fastest", "label": "Fastest", "intent": "quest then tree", "step_ids": ["S01b", "S03", "S04"]}],
        "steps": [
          {"step_id": "S01", "kind": "train", "title": "Fixture rock", "method": "Rock", "until_level": 8, "xp_per_action": F("C-MTH-001", 10),
           "xp_per_hour": F("C-MTH-002", 5000), "facts": [fx["C-MTH-001"]], "rationale": "no damage source at all"},
          {"step_id": "S02", "kind": "train", "title": "Fixture rock to 20", "method": "Rock", "until_level": 20, "xp_per_action": F("C-MTH-001", 10),
           "xp_per_hour": F("C-MTH-002", 5000), "facts": [fx["C-MTH-001"]], "rationale": "still no damage source"},
          {"step_id": "S01b", "kind": "train", "title": "Fixture rock to 8", "method": "Rock", "until_level": 8, "xp_per_action": F("C-MTH-001", 10),
           "xp_per_hour": F("C-MTH-002", 5000), "facts": [fx["C-MTH-001"]], "rationale": "reach tree requirement"},
          {"step_id": "S03", "kind": "quest", "title": "Fixture quest", "xp_rewards": [{"skill": "Fixture", "xp": F("C-QST-001", 500)},
                                                                                       {"skill": "Defence", "xp": F("C-QST-002", 150)}],
           "facts": [fx["C-QST-001"]], "rationale": "skips slow levels", "update_refs": ["U-001"]},
          {"step_id": "S04", "kind": "train", "title": "Fixture tree", "method": "Tree", "until_level": 20, "min_level": 8,
           "xp_per_action": F("C-MTH-003", 25), "xp_per_hour": F("C-MTH-004", 12000),
           "supplies_per_action": [{"item": "Fixture axe polish", "qty": F("C-LOG-001", 1)}],
           "requirements": [{"type": "skill", "skill": "Fixture", "level": 8, "fact": fx["C-MTH-005"]}],
           "facts": [fx["C-MTH-003"]], "rationale": "fastest XP"}],
        "decision_points": [{"dp_id": "DP01", "at_level": 1, "until_level": 8, "question": "Rock or quest first?",
            "options": [{"option_id": "A", "title": "Rock all the way", "step_ids": ["S01", "S02"], "justification": "no damage source anywhere on this option",
                         "pros": ["safe"], "cons": ["slow"]},
                        {"option_id": "B", "title": "Quest then tree", "step_ids": ["S01b", "S03", "S04"], "justification": "faster but tree failures can hurt",
                         "pros": ["fast"], "cons": ["damage"], "best_for": "players with food"}],
            "recommended": "A", "recommendation_reason": "fixture"}],
        "assumptions": ["synthetic"], "provenance": prov("route-strategist", ["facts.json", "brief.json"])}
    write("plan.json", plan)
    run(py, "tools/validate.py", JOB, "plan")
    run(py, "tools/ledger.py", "seal", JOB, "plan.json", "--author", "route-strategist")
    # build-cap enforcement: a Defence cap of 1 must make the quest route fail, cap 3 (150 xp -> lvl 2) passes
    b = json.loads((J / "brief.json").read_text())
    run(py, "tools/xp.py", "simulate", JOB)
    calc = json.loads((J / "calc.json").read_text())
    assert calc["routes"]["fastest"]["capped_skills"]["Defence"]["end_level"] == 2, "defence tracking"
    print("PASS defence XP from quests tracked (fastest route ends at Defence 2 of cap 3)")
    run(py, "tools/ledger.py", "seal", JOB, "calc.json", "--author", "quant", expect=1)  # only 'system' may seal calc
    run(py, "tools/ledger.py", "seal", JOB, "calc.json", "--author", "system")
    write("calc-review.json", {"calc_sha256": sha("calc.json"), "findings": [], "decision": "pass", "provenance": prov("quant", ["calc.json", "plan.json"])})
    run(py, "tools/validate.py", JOB, "calc")
    run(py, "tools/ledger.py", "seal", JOB, "calc-review.json", "--author", "quant")

    def zero(**over):
        base = {k: {"score": 0, "rationale": "none"} for k in ("lethality", "pvp", "escape", "attention", "disconnect", "unpredictability", "exposure", "knowledge")}
        for k, v in over.items():
            base[k] = v
        return base
    entry = lambda sid, factors, flags=(): {"step_id": sid, "factors": factors, "flags": list(flags),
        "hw_death_classification": {"status": "UNSAFE_DEATH" if factors["lethality"]["score"] else "NO_DEATH_POSSIBLE", "note": "fixture"},
        "mitigations": [], "preconditions": {"min_hitpoints": 10, "stop_conditions": ["fixture"]}, "bailout": "walk away", "verdict": "approve"}
    risk = {"profile_basis": {"Hitpoints": 10}, "risk_appetite": "standard",
            "entries": [entry("S01", zero(exposure={"score": 3, "rationale": "hours"})), entry("S02", zero()), entry("S01b", zero()), entry("S03", zero()),
                        entry("S04", zero(lethality={"score": 2, "rationale": "2 dmg fails", "facts": [fx["C-THR-001"]]},
                                          attention={"score": 2, "rationale": "eat"}, exposure={"score": 3, "rationale": "hours"}),
                              ["LOW_HP_SKILLING_DAMAGE", "NEW_CONTENT"])],
            "route_verdicts": [{"route_id": "safest", "verdict": "approve"}, {"route_id": "fastest", "verdict": "approve"}],
            "general_rules": ["fixture rule"], "provenance": prov("risk-officer", ["plan.json", "calc.json"])}
    write("risk.json", risk)
    run(py, "tools/danger.py", "score", JOB, "--appetite", "standard")
    run(py, "tools/validate.py", JOB, "risk")
    run(py, "tools/ledger.py", "seal", JOB, "risk.json", "--author", "risk-officer")
    write("redteam.json", {"attack_surface": ["fixture"], "findings": [{"finding_id": "RT-01", "severity": "high", "step_id": "S04",
        "scenario": "fixture scenario for gate test", "recommendation": "fix", "status": "open"}], "provenance": prov("red-team", ["risk.json"])})
    run(py, "tools/validate.py", JOB, "redteam", expect=1)  # open high finding must block
    rt = json.loads((J / "redteam.json").read_text()); rt["findings"][0]["status"] = "fixed"; rt["findings"][0]["resolution"] = "fixture"
    write("redteam.json", rt)
    run(py, "tools/validate.py", JOB, "redteam")
    run(py, "tools/ledger.py", "seal", JOB, "redteam.json", "--author", "red-team")

    prose = {"title": "Fixture 1–20 (self-test)", "subtitle": "synthetic", "intro": "Synthetic fixture guide.",
             "steps": [{"step_id": s["step_id"], "summary": "Do the fixture thing.", "instructions": ["Perform {{step.actions}} actions over {{step.hours}}."],
                        "warnings": ["Stay above {{risk.min_hitpoints}} hitpoints."]} for s in plan["steps"]],
             "provenance": prov("guide-author", ["plan.json", "risk.json"])}
    write("prose.json", prose)
    run(py, "tools/validate.py", JOB, "prose")
    bad = json.loads(json.dumps(prose)); bad["steps"][0]["summary"] = "Do it 500 times."
    write("prose.json", bad)
    run(py, "tools/validate.py", JOB, "prose", expect=1)  # bare number rejected
    write("prose.json", prose)
    run(py, "tools/ledger.py", "seal", JOB, "prose.json", "--author", "guide-author")
    run(py, "tools/assemble.py", JOB)
    run(py, "tools/ledger.py", "seal", JOB, "content.json", "--author", "system")
    run(py, "tools/render.py", JOB)
    run(py, "tools/validate.py", JOB, "html")
    r = run("node", "tools/browser_check.mjs", f"jobs/{JOB}/guide.html", expect=None)
    print("      " + r.stdout.strip().replace("\n", "\n      "))
    if "FAIL" in r.stdout:
        global fails
        fails += 1
    run(py, "tools/ledger.py", "released", JOB, expect=1)
    run(py, "tools/ledger.py", "sign", JOB, "--role", "qa", "--author", "route-strategist", "--subject", "content.json", "--decision", "approve", expect=1)
    write("qa.json", {"content_sha256": sha("content.json"), "checks": [{"check": c, "result": "pass"} for c in "abcde"],
                      "spot_checks": [], "decision": "approve", "reasons": ["fixture"], "provenance": prov("qa-auditor", ["content.json"])})
    run(py, "tools/ledger.py", "seal", JOB, "qa.json", "--author", "qa-auditor")
    run(py, "tools/ledger.py", "sign", JOB, "--role", "qa", "--author", "qa-auditor", "--subject", "content.json", "--decision", "approve")
    run(py, "tools/ledger.py", "released", JOB)
    run(py, "tools/render.py", JOB)
    run(py, "tools/ledger.py", "seal", JOB, "guide.html", "--author", "system")
    run(py, "tools/validate.py", JOB, "release")

    # ---- attacks on the controls -------------------------------------------------
    (J / "plan.json").write_text((J / "plan.json").read_text().replace('"until_level": 20', '"until_level": 21', 1))
    run(py, "tools/ledger.py", "verify", JOB, expect=1)          # tamper detected
    run(py, "tools/ledger.py", "released", JOB, expect=1)        # release revoked by tamper
    run(py, "tools/assemble.py", JOB, expect=1)                  # assembler refuses tampered input
    (J / "ledger.jsonl").write_text((J / "ledger.jsonl").read_text().replace('"author": "intake-officer"', '"author": "director"', 1))
    run(py, "tools/ledger.py", "verify", JOB, expect=1)          # ledger rewrite detected

    sentry = lambda payload, expect: run(py, "tools/sentry.py", stdin=json.dumps(payload), expect=expect)
    (TMP / "jobs" / ".active").write_text(JOB)
    P = lambda tool, ti, agent=None: {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti, "session_id": "t",
                                      **({"agent_type": agent, "agent_id": "a1"} if agent else {})}
    sentry({"hook_event_name": "SubagentStart", "agent_type": "methods-analyst", "agent_id": "a1"}, 0)
    sentry(P("Write", {"file_path": str(J / "facts.json"), "content": "x"}, "fact-verifier"), 2)        # sealed
    sentry(P("Write", {"file_path": str(J / "risk.json"), "content": "x"}, "route-strategist"), 2)      # sealed + out of scope
    sentry(P("Write", {"file_path": str(J / "research/claims-rfi-01.json"), "content": "x"}, "guide-author"), 2)  # out of scope
    sentry(P("Write", {"file_path": str(J / "research/claims-rfi-01.json"), "content": "x"}, "quest-archivist"), 0)
    sentry(P("Write", {"file_path": str(TMP / "tools/xp.py"), "content": "x"}, "quant"), 2)            # tooling protected
    sentry(P("Write", {"file_path": str(TMP / "audit/actions.jsonl"), "content": "x"}), 2)               # audit append-only
    sentry(P("Write", {"file_path": str(TMP / "templates/guide.html"), "content": "x"}, "guide-author"), 2)
    sentry(P("Bash", {"command": "python3 tools/xp.py xp 50"}, "quant"), 0)
    sentry(P("Bash", {"command": "python3 tools/wiki.py page X"}, "route-strategist"), 2)              # no web for planners
    sentry(P("Bash", {"command": "python3 tools/ledger.py verify " + JOB}, "guide-author"), 0)          # read-only ledger OK
    sentry(P("Bash", {"command": "python3 tools/ledger.py seal " + JOB + " plan.json --author route-strategist"}, "route-strategist"), 2)
    sentry(P("Bash", {"command": "python3 tools/xp.py xp 5 && rm -rf jobs"}, "quant"), 2)               # chaining
    sentry(P("Bash", {"command": "echo hi > jobs/x"}, "quant"), 2)                                        # redirection
    sentry(P("Bash", {"command": "curl https://example.com"}), 2)
    sentry(P("WebFetch", {"url": "https://oldschool.runescape.wiki/w/X"}, "risk-officer"), 2)          # no web for risk officer
    sentry(P("WebFetch", {"url": "https://oldschool.runescape.wiki/w/X"}, "threat-analyst"), 0)
    sentry(P("Agent", {"subagent_type": "quant", "prompt": "undocumented instructions"}), 0)              # allowed, but...
    run(py, "tools/audit.py", "verify")
    r = run(py, "tools/audit.py", "crosscheck", JOB, expect=1)                                            # ...crosscheck flags it
    print("      " + "\n      ".join(l for l in r.stdout.splitlines() if "undocumented" in l or "TAMPER" in l))
    gov = {**ENV, "OSRS_GOVERNANCE_MODE": "1"}
    run(py, "tools/sentry.py", stdin=json.dumps(P("Write", {"file_path": str(TMP / "tools/xp.py"), "content": "x"})), expect=0, env=gov)
    run(py, "tools/sentry.py", stdin=json.dumps(P("Write", {"file_path": str(TMP / "audit/actions.jsonl"), "content": "x"})), expect=2, env=gov)
    lines = (TMP / "audit/actions.jsonl").read_text().splitlines()
    tampered = json.loads(lines[2]); tampered["decision"] = "allow"
    lines[2] = json.dumps(tampered)
    (TMP / "audit/actions.jsonl").write_text("\n".join(lines) + "\n")
    run(py, "tools/audit.py", "verify", expect=1)                                                         # audit log tamper detected
    run(py, "tools/audit.py", "export", JOB)

    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILURE(S)'}  (workspace: {TMP})")
    if not fails:
        shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
