---
name: osrs-refresh
description: Maintenance sweep for a released guide - re-runs the Patch Sentinel from the guide's last update date, has the Fact Verifier re-check every fact the guide relies on against current wiki revisions, and opens a revision job if anything changed. Use weekly, after any major game update, or as "/osrs-refresh <job>".
---

# /osrs-refresh: keep a released guide current

Target job: **$ARGUMENTS**

Game updates happen every week, and a guide that was right last month can kill someone today.

1. Read `jobs/<job>/content.json`: note `meta.updates_as_of`, `meta.facts_as_of`, and the list of facts used.
2. Open a maintenance job `<job>-refresh-<yyyymmdd>` (`ledger.py init`). Copy nothing into it; it reads the original job's sealed files by path.
3. Following the dispatch protocol in /osrs-guide, dispatch **patch-sentinel**. Window: from the original `updates_as_of` to today. Task: find updates that touch the guide's skill, methods, quests, locations or death rules.
4. Dispatch **fact-verifier**. Task: re-fetch the current revision of every source behind the original guide's facts and mark each fact unchanged, STALE or DISPUTED. Output `facts.json` in the refresh job; claims come from the original job's research files plus the new updates.json.
5. Decide with the owner:
   - **No relevant change:** record a `decision` event ("guide still current as of <date>") and tell the owner.
   - **Changes found:** list them (fact, old value, new value, affected steps). With the owner's agreement, run `/osrs-guide` as a revision: brief = the original brief plus "revise for: <changes>". The original job's sealed artifacts stay as the audit baseline.
6. `python3 tools/audit.py export <refresh-job>`, then report.
