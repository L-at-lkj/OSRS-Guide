You are the ROUTE STRATEGIST of the OSRS Guide Company. Your charter: /home/user/osrs-guide-company/.claude/agents/route-strategist.md (sha256 prefix c27530fbc7d7). Follow it and the constitution exactly. No web access. Work from /home/user/osrs-guide-company.
ROLE: route-strategist
JOB: agility-1-99-20261119 | TODAY: 2026-11-20
TASK: Revise your plan.json (the Director unsealed it at ledger seq 128) to honour the Risk Officer's vetoes in the sealed risk.json (5e2f34f18337). The Director cannot override a veto.
1. Remove steps S17 (Troll Romance), S23 (Werewolf course), S24 (Sins of the Father) and S25 (Hallowed Sepulchre), and remove the `fastest` route (vetoed: it depends on S23). Remove S22 (Creature of Fenkenstrain) too, since its only Agility purpose was S23.
2. Repair the decision points that referenced them, using ONLY existing remaining steps (do not add new steps; any new step would need a new danger rating):
   - DP03: drop option C; keep A (skip) and B (S15+S16). The owner has explicitly ACCEPTED the risk of S16 Troll Stronghold (ledger accept_risk seq 126), so B is a legitimate owner-accepted option, but keep the Risk Officer's recommendation (A) unless you have a fact-based reason.
   - DP05: Werewolf is gone. Either remove DP05, or turn it into a real fork between existing steps (e.g. Seers' S09 vs Canifis S07 from 60) if facts support it.
   - DP07: the Sepulchre is gone. Either remove DP07, or keep a two-option fork from existing steps. Mention in assumptions that the Sepulchre and Werewolf were vetoed at the owner's current 48 HP and will be re-rated by a future guide revision once Hitpoints and combat rise. That is the owner's long-term "next step".
3. The owner accepted S05 Underground Pass, S06 Regicide and S12 The Fremennik Trials (ledger accept_risk seq 123-125), so the balanced route stands as is.
4. Fold the Quant's findings into `assumptions`: route totals exclude quest time; the balanced-vs-safest gap is mostly Rellekka vs Pollnivneach, not the quests; Seers' 40,000 XP/h is optimistic while you still fail obstacles (27,000-37,000).
Then check: `python3 tools/xp.py simulate agility-1-99-20261119 --out calc-draft.json` has no errors, `python3 tools/validate.py agility-1-99-20261119 plan` shows 0 FAIL, and `python3 tools/validate.py agility-1-99-20261119 risk` shows 0 FAIL (removed vetoed steps then show as "veto honoured" warnings). Update your provenance (inputs incl. risk.json, the decisions you made).
SEALED INPUTS: brief.json (c27aa6bc9969), facts.json (70fcb7eed3ab), risk.json (5e2f34f18337), calc-review.json, ledger entries 123-128.
OUTPUT: jobs/agility-1-99-20261119/plan.json
DONE WHEN: the three checks pass. Do not seal. Short report listing the final routes and decision points.
