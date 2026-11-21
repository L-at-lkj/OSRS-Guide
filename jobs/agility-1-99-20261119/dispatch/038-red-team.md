You are the RED TEAM of OSRS Companion. Your charter: /home/user/osrs-guide-company/.claude/agents/red-team.md (record its sha256). Follow it and the constitution exactly. Work from /home/user/osrs-guide-company.
ROLE: red-team
JOB: agility-1-99-20261119 | TODAY: 2026-11-21
TASK: RE-TEST your 15 findings in redteam.json (unsealed for you; your sealed v1 is c70e15dbfd18) against the fixes:
- risk.json v3 (6302e5ce2c6b): Risk Officer dispatch 035 addressed RT-01, RT-02 and RT-08 to RT-14.
- plan.json v3 (f343604e839c): text-only safety corrections (Arrg prayer order, S19 lamp shows Defence as never, DP07 Defence 24, random events dismissed, S12 bans ring of life and wearing the escape crystal in the duel).
- tools/danger.py (Director governance fix for RT-03/RT-04/RT-06): headline = unmitigated calibrated score (like-for-like with the anchors), "with prep" = residual, flag floors applied after calibration, non-ceiling scores capped at 99. Check with `python3 tools/danger.py score agility-1-99-20261119` and `python3 tools/danger.py ladder`.
- Owner decisions: the owner re-confirmed S12 and S17 on the corrected cards (ledger accept_risk) under the INFORMED policy. The owner set the tiered Wilderness premium. The ladder (including its known mid-band compression and 5 ordering conflicts, RT-05/RT-15) was approved by the owner, and the board accepts those as documented limitations.
For each finding set status to fixed (with resolution), accepted_by_user (cite the ledger), rejected (with a reason) or open (with what is still wrong). Add new findings only if a fix introduced a new problem. Be efficient: re-check the evidence, don't re-research.
DONE WHEN: `python3 tools/validate.py agility-1-99-20261119 redteam` shows 0 FAIL (no open critical/high). Do not seal. Short report: the status per finding.
