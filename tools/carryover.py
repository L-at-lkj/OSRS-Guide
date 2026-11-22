#!/usr/bin/env python3
"""Carry verified facts from an earlier job into a new one, mechanically.

A fact is carried only if (a) it was VERIFIED or VERIFIED_WITH_CAVEAT in the
source job's sealed facts.json, (b) it matches the selection patterns, and
(c) EVERY wiki source it cites is still at the same revision today (checked
live through the MediaWiki API). Facts whose pages changed are listed for
fresh verification instead. Nothing is re-interpreted: value, statement and
sources are copied as they are, with a caveat naming the origin and the check date.

  python3 tools/carryover.py <from_job> <to_job> --match REGEX [--match REGEX ...]

Writes jobs/<to_job>/facts-parts/carryover.json (fact ids F-6001.., claim ids
"carry:<from_job>:<fact_id>"), sealed by `system`. validate.py checks every
carried fact against its origin.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import die, job_dir, load_json, now_iso, save_json, sha256_file, today  # noqa: E402
import ledger  # noqa: E402
import wiki  # noqa: E402

GOOD = {"VERIFIED", "VERIFIED_WITH_CAVEAT"}


def current_revids(revids: set[int]) -> dict[int, int | None]:
    """revid -> latest revid of its page (None if unknown)."""
    out = {}
    ids = sorted(revids)
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        data = wiki.api({"action": "query", "revids": "|".join(map(str, chunk)), "prop": "info"})
        pages = data.get("query", {}).get("pages", [])
        latest_by_page = {p.get("pageid"): p.get("lastrevid") for p in pages}
        # map each requested revid to its page's lastrevid via a second lookup
        d2 = wiki.api({"action": "query", "revids": "|".join(map(str, chunk)), "prop": "revisions", "rvprop": "ids"})
        for p in d2.get("query", {}).get("pages", []):
            for r in p.get("revisions", []):
                out[r["revid"]] = latest_by_page.get(p.get("pageid"))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("from_job"); p.add_argument("to_job")
    p.add_argument("--match", action="append", required=True, help="regex on subject/attribute/statement")
    a = p.parse_args()
    src = job_dir(a.from_job) / "facts.json"
    st = ledger.seal_state(ledger.read_entries(a.from_job)).get("facts.json")
    if not st or not st["sealed"] or sha256_file(src) != st["sha256"]:
        die(f"{a.from_job}/facts.json is not sealed or differs from its seal")
    rx = [re.compile(m, re.I) for m in a.match]
    picked = [f for f in load_json(src)["facts"] if f["status"] in GOOD and
              any(r.search(f"{f['subject']} {f['attribute']} {f['statement']}") for r in rx)]
    revids = {s["revid"] for f in picked for s in f["sources"] if s.get("revid") and "oldschool.runescape.wiki" in s["url"]}
    latest = current_revids(revids) if revids else {}
    carried, stale = [], []
    n = 6001
    for f in picked:
        wiki_srcs = [s for s in f["sources"] if s.get("revid") and "oldschool.runescape.wiki" in s["url"]]
        changed = [s["revid"] for s in wiki_srcs if latest.get(s["revid"]) not in (s["revid"],)]
        if not wiki_srcs or changed:
            stale.append({"fact_id": f["fact_id"], "subject": f["subject"], "changed_revids": changed or "no wiki source"})
            continue
        carried.append({**f, "fact_id": f"F-{n:04d}", "claim_id": f"carry:{a.from_job}:{f['fact_id']}",
                        "status": "VERIFIED_WITH_CAVEAT",
                        "caveat": ((f.get("caveat") + " | ") if f.get("caveat") else "") +
                                  f"Carried over from {a.from_job} {f['fact_id']}; every cited wiki revision was still current on {today()}.",
                        "verified_at": today()})
        n += 1
    out = {"as_of": today(), "facts": carried, "rfi": [],
           "provenance": {"agent": "fact-verifier", "started_at": now_iso(), "finished_at": now_iso(),
                          "inputs": [{"path": f"jobs/{a.from_job}/facts.json", "sha256": st["sha256"]}],
                          "actions": [{"kind": "verify", "detail": f"tools/carryover.py: {len(revids)} wiki revisions checked live against the current revision; patterns {a.match}"}],
                          "decisions": [{"decision": f"carried {len(carried)}, sent {len(stale)} for re-verification",
                                         "reason": "carry only facts whose every cited wiki revision is unchanged"}],
                          "limitations": [f"not carried (source changed or no wiki source): {[s['fact_id'] for s in stale]}"]}}
    save_json(job_dir(a.to_job) / "facts-parts" / "carryover.json", out)
    print(json.dumps({"carried": len(carried), "needs_reverification": stale}, indent=1)[:3000])


if __name__ == "__main__":
    main()
