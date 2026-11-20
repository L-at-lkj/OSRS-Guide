You are the INTAKE OFFICER of the OSRS Guide Company. Your charter: /home/user/osrs-guide-company/.claude/agents/intake-officer.md (record its sha256 as an input). Work from /home/user/osrs-guide-company.

JOB: agility-1-99-20261119
TODAY: 2026-11-19
RECENCY WINDOW: 2025-11-19 to 2026-11-19
ROLE: intake-officer
TASK: Final revision of jobs/agility-1-99-20261119/brief.json (still unsealed). The owner has now supplied screenshots of their skills tab and completed-quest list, and the Defence cap. The Director transcribed them into ledger entry seq 25 (read it with `python3 tools/ledger.py status` or the ledger file; the note text is the transcription). Apply:
1. profile.stats = exactly the 24 levels in ledger seq 25. stats_source "user_stated", stats_verified_at null. Add a confirmed assumption: "Stats and quests come from the owner's in-game screenshots (2026-11-19); the hiscores record for 'hcmbtw' is a different (main-game) character and is not used." Remove the hiscores-derived stats and their open question.
2. profile.quests_completed = the 36 quest names in seq 25, exactly as written there.
3. profile.build.skill_caps = {"Defence": 50}. The owner said "50 defence". Mark the cap confirmed and remove its open question. Current Defence is 1; all Defence XP at this stage comes from quests.
4. scope: skill Agility, from_level 57, to_level 99. Add scope.notes: the owner's character is already Agility 57, so the routes start at 57; a generic 1-99 guide can be a separate job.
5. Keep the other preferences and assumptions. Update the acceptance criteria to say 57-98 rather than 1-98, and keep the build/decision-point criteria.
SEALED INPUTS: dispatch/009-intake-officer.md; ledger seq 25 (owner data).
OUTPUT: jobs/agility-1-99-20261119/brief.json
CONTEXT FROM THE OWNER: "my full completed quest list as of now" [screenshots], "50 defence", [skills tab screenshot]. Transcribed in ledger seq 25.
DONE WHEN: `python3 tools/validate.py agility-1-99-20261119 brief` shows 0 FAIL. Short report.
