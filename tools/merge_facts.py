#!/usr/bin/env python3
"""Merge parallel Fact Verifier parts into facts.json, deterministically.

Large jobs run several fact-verifier instances in parallel, one per research
desk, each writing jobs/<job>/facts-parts/<desk>.json with its own fact-id
range, so the merge never renumbers anything:
    updates 0001-0999 · methods 1000-1999 · quests 2000-2999
    threats 3000-3999 · logistics 4000-4999 · rfi 5000-5999
Every part must be sealed (author fact-verifier) before merging. The output
is sealed by `system`.

  python3 tools/merge_facts.py <job>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import die, job_dir, load_json, now_iso, save_json, sha256_file, validate_against  # noqa: E402
import ledger  # noqa: E402

RANGES = {"updates": (1, 999), "methods": (1000, 1999), "quests": (2000, 2999), "threats": (3000, 3999),
          "logistics": (4000, 4999), "rfi": (5000, 5999)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("job")
    a = p.parse_args()
    d = job_dir(a.job)
    state = ledger.seal_state(ledger.read_entries(a.job))
    parts = sorted((d / "facts-parts").glob("*.json"))
    if not parts:
        die("no facts-parts/*.json")
    facts, rfi, inputs, actions, decisions, limitations, seen = [], [], [], [], [], [], set()
    as_of = []
    for part in parts:
        rel = part.relative_to(d).as_posix()
        st = state.get(rel)
        if not st or not st["sealed"] or sha256_file(part) != st["sha256"]:
            die(f"{rel} is not sealed or differs from its seal")
        data = load_json(part)
        errs = validate_against(data, "facts")
        if errs:
            die(f"{rel} schema: {errs[:5]}")
        desk = part.stem
        lo, hi = RANGES.get(desk, (0, 9999))
        for f in data["facts"]:
            n = int(f["fact_id"][2:])
            if not lo <= n <= hi:
                die(f"{rel}: {f['fact_id']} outside the {desk} range F-{lo:04d}..F-{hi:04d}")
            if f["fact_id"] in seen:
                die(f"duplicate {f['fact_id']}")
            seen.add(f["fact_id"])
            facts.append(f)
        rfi += data.get("rfi", [])
        as_of.append(data["as_of"])
        prov = data["provenance"]
        inputs += prov["inputs"] + [{"path": rel, "sha256": st["sha256"]}]
        actions += [{**x, "detail": f"[{desk}] {x['detail']}"} for x in prov["actions"]]
        decisions += [{**x, "decision": f"[{desk}] {x['decision']}"} for x in prov["decisions"]]
        limitations += [f"[{desk}] {x}" for x in prov["limitations"]]
    facts.sort(key=lambda f: f["fact_id"])
    out = {"as_of": max(as_of), "facts": facts, "rfi": rfi,
           "provenance": {"agent": "fact-verifier", "started_at": now_iso(), "finished_at": now_iso(),
                          "inputs": inputs, "actions": actions + [{"kind": "compute", "detail": "merged by tools/merge_facts.py"}],
                          "decisions": decisions, "limitations": limitations}}
    save_json(d / "facts.json", out)
    print(f"facts.json: {len(facts)} facts from {len(parts)} parts; {len(rfi)} RFIs")


if __name__ == "__main__":
    main()
