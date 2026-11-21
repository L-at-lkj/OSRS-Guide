You are the RED TEAM of OSRS Companion (charter: /home/user/osrs-guide-company/.claude/agents/red-team.md; record its sha256). Work from /home/user/osrs-guide-company. Keep this short and efficient.
JOB: agility-1-99-20261119 | TODAY: 2026-11-21
TASK: update redteam.json (unsealed for you):
1. RT-05, RT-07, RT-15: QA (qa.json, ledger seq 191, R2) found that these were marked accepted_by_user without an owner acceptance. The owner has now decided, verbatim: "Re-open all three" (ledger decision after seq 191). Set all three to status "open", with resolution "re-opened by owner; scheduled for the next calibration revision; no route step of this guide is affected".
2. RT-16: re-test against risk.json (sealed; S12-M6 says bank the escape crystal before the duel) and plan.json v4 (5a0296c74446; route-strategist 042 changed the S12 rationale, the checklist and DP02-B/DP08-B to "bank it before the duel"). Set fixed or open with a reason.
Add no other findings unless the fix created a new problem. DONE WHEN `python3 tools/validate.py agility-1-99-20261119 redteam` shows 0 FAIL (open medium/low are fine). Update provenance. Do not seal. One-paragraph report.
