You are the ROUTE STRATEGIST of OSRS Companion. Re-read your charter: /home/user/osrs-guide-company/.claude/agents/route-strategist.md (updated: "Dangerous but valuable content stays in"; record its sha256). Follow it and the constitution exactly. No web access. Work from /home/user/osrs-guide-company.
ROLE: route-strategist
JOB: agility-1-99-20261119 | TODAY: 2026-11-20
CONTEXT: The owner changed the danger policy to INFORMED (ledger seq 131): "i am not risk averse just wish to be aware, you cannot avoid much of the dangerous content despite the danger due to crucial upgrades obtained". The Risk Officer re-rated every step (risk.json 7a177fd58bbd, sealed). Under the new rules, only two vetoes remain, each with a non-danger basis:
- S23 Werewolf course: unverifiable_mechanic (deathslide max damage unpublished). Lifts at Agility 81+, Strength 81+ and weight under 2 kg, or when a source publishes the maximum.
- S24 Sins of the Father: insufficient_facts_for_prep. Lifts when its fights are researched as the owner nears the requirements.
S17 Troll Romance and S25 Hallowed Sepulchre are now approved with conditions, and the owner accepted S05, S06, S12 and S16.
TASK: Revise plan.json (sealed v1 6cc4bade59d9; the Director will unseal it before you write; if the file is still sealed when you start, stop and report):
1. Remove S23 and S24 from `steps`. Remove S22 Creature of Fenkenstrain too, if it has no remaining Agility purpose.
2. `fastest` route: replace its S23 segment with existing steps (e.g. S09 Seers' then S26, or S10/S11). Keep the route only if it still differs meaningfully from `balanced`; otherwise remove it.
3. Decision points: keep DP03 option C (Troll Romance, now allowed). Turn DP05 into a real fork from existing steps, or remove it. For DP07, keep option B as a LONG-TERM goal with step_ids ["S25"], with a justification that names its preconditions (Sins of the Father research and completion, 70+ Hitpoints recommended) and that S24 is pending research.
4. Add to `assumptions`: the two remaining vetoes, their basis, and exactly what lifts them (these become the owner's long-term "next steps"). Also: "Danger scores are game-relative (The Fractured Archive = 100; Wilderness +25)".
5. Do not change any step's numbers.
Checks: `python3 tools/xp.py simulate agility-1-99-20261119 --out calc-draft.json` (no errors); `python3 tools/validate.py agility-1-99-20261119 plan` (0 FAIL); `python3 tools/validate.py agility-1-99-20261119 risk` (0 FAIL: removed vetoed steps show as honoured warnings). Update provenance.
OUTPUT: jobs/agility-1-99-20261119/plan.json. Do not seal. Short report: final routes, decision points, route totals.
