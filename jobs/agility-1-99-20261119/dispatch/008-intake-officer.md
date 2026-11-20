You are the INTAKE OFFICER of the OSRS Guide Company. Re-read your charter at /home/user/osrs-guide-company/.claude/agents/intake-officer.md (regenerated, sha256 prefix d0ba11d70208; record it as an input) and the updated schemas/brief.schema.json, which now has profile.build. Work from /home/user/osrs-guide-company.

JOB: agility-1-99-20261119
TODAY: 2026-11-19
RECENCY WINDOW: 2025-11-19 to 2026-11-19
ROLE: intake-officer
TASK: Revise jobs/agility-1-99-20261119/brief.json (unsealed by the Director for this purpose). The owner wrote, verbatim: "note that i am following a zerker style build using quests for all defense4 exp at this stage ensure that is considered and  next step suggestions can be provided with multiple options along with justification to assist me throughout my journey".
1. Add profile.build: archetype "zerker" (a berserker-style build), skill_caps {"Defence": 45}, xp_rules (e.g. "Defence XP only from quest rewards at this stage"; "never train Defence directly or choose it for a lamp"; "never use a combat style that gives Defence XP"), lamp_policy "never Defence", confirmed true. The cap of 45 is the conventional zerker cap; the owner said "zerker style" without a number, so add an unconfirmed assumption "Defence cap is 45" and an open question to confirm it.
2. Add acceptance criteria: "no route pushes Defence above the build cap (tracked by the XP engine)"; "every quest used lists its Defence XP so the cap can be tracked"; "the guide offers next-step decision points with 2+ justified options at each meaningful fork".
3. Keep everything else from your previous brief (the hiscores-verified fresh stats, the preferences). Keep the open question about whether the hiscores record is the Hardcore Worlds character.
SEALED INPUTS: dispatch/008-intake-officer.md; your previous brief content is in the file itself (unsealed v1, sha256 dfabd8f3db7e at seal).
OUTPUT: jobs/agility-1-99-20261119/brief.json (schema: schemas/brief.schema.json)
CONTEXT FROM THE OWNER: as quoted above, plus earlier answers: Standard HW account (trades/GE), member, risk cap Standard 44, account name hcmbtw.
DONE WHEN: `python3 tools/validate.py agility-1-99-20261119 brief` shows 0 FAIL. Short report.
