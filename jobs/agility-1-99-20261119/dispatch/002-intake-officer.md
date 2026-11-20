You are the INTAKE OFFICER of the OSRS Guide Company. Re-read your charter at /home/user/osrs-guide-company/.claude/agents/intake-officer.md (it was regenerated; record its current sha256 as an input) and follow it exactly. Work from /home/user/osrs-guide-company.

JOB: agility-1-99-20261119
TODAY: 2026-11-19
RECENCY WINDOW: 2025-11-19 to 2026-11-19
ROLE: intake-officer
TASK: Revise your brief at jobs/agility-1-99-20261119/brief.json (it is unsealed, so you may overwrite it). The owner has answered: their account name is "hcmbtw" (verbatim: "name is hcmbtw").
1. Look the account up with tools/hiscores.py: try `lookup hcmbtw --mode normal` and the hardcore/ironman modes. The character lives on Hardcore Worlds, whose hiscores endpoint may differ (see the docstring), so note which endpoint returned data and whether it is likely the Hardcore Worlds character. Also try `wikisync hcmbtw` for quests and diaries; it only works if the owner uses the RuneLite WikiSync plugin.
2. Put the verified stats into profile.stats with stats_source "hiscores" (or "wikisync"), plus stats_verified_at. If the stats look like a different character (e.g. a main-game account with the same name), say so plainly in assumptions (confirmed: false) and in open_questions.
3. The owner did not answer the optimisation, attention, budget or exclusion questions. Keep those as unconfirmed assumptions with your defaults and remove them from open_questions (the owner has seen them once).
4. Record every lookup in provenance. A Director reachability probe of the normal-mode hiscores just happened; it is not your evidence, so do your own lookups.
SEALED INPUTS: dispatch/002-intake-officer.md
OUTPUT: jobs/agility-1-99-20261119/brief.json (schema: schemas/brief.schema.json)
CONTEXT FROM THE OWNER: "name is hcmbtw". Earlier answers: Standard HW account (trades/GE), member, risk cap Standard 44.
DONE WHEN: `python3 tools/validate.py agility-1-99-20261119 brief` shows 0 FAIL. Finish with a short report that includes the key stats (Agility, Hitpoints, combat-relevant skills) and quests/diaries if found.
