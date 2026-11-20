You are the INTAKE OFFICER of the OSRS Guide Company. Your charter was updated (sha256 prefix 0fa00eeaea62): re-read /home/user/osrs-guide-company/.claude/agents/intake-officer.md, especially step 3 on Hardcore Worlds hiscores. Work from /home/user/osrs-guide-company.

JOB: agility-1-99-20261119
TODAY: 2026-11-19
RECENCY WINDOW: 2025-11-19 to 2026-11-19
ROLE: intake-officer
TASK: Verify the owner's stats against the HARDCORE WORLDS hiscores and finalise brief.json (still unsealed).
The owner wrote, verbatim: "ensure when checking hiscores you use the hardcore worlds hiscores as normal hiscores do not show hardcore world progress".
1. Run `python3 tools/hiscores.py lookup hcmbtw` (the default board is now hardcore_worlds = m=hiscore_oldschool_hardcore_mains). Record the endpoint, the timestamp, and the level and XP of every skill.
2. Compare with the owner's screenshot transcription (ledger seq 25). Hiscores refresh on logout, so where the screenshot is higher it is the newer value. Use the screenshot level in profile.stats, and list every difference in an assumption, e.g. "Hitpoints 48 (screenshot) vs 47 (HW hiscores, pre-logout)". Set stats_source "hiscores" and stats_verified_at to your lookup time if all other skills match; otherwise explain.
3. Add profile.skill_xp with the exact hiscores XP for Agility (and Defence), so the XP engine can start from the exact Agility XP. Note that Agility XP may be slightly higher in game if the owner has trained since their last logout.
4. Remove the earlier note that the hiscores record is a different character. The earlier lookups used the NORMAL board, which does not show Hardcore Worlds progress. Correct that statement in assumptions and provenance (keep the old lookups in provenance, marked "wrong board, superseded").
5. Keep everything else (quests, Defence cap 50, zerker build, scope 57-99, preferences).
SEALED INPUTS: dispatch/010-intake-officer.md; ledger seq 25 and seq 29.
OUTPUT: jobs/agility-1-99-20261119/brief.json
CONTEXT FROM THE OWNER: as quoted above.
DONE WHEN: `python3 tools/validate.py agility-1-99-20261119 brief` shows 0 FAIL. Short report, including the exact Agility XP.
