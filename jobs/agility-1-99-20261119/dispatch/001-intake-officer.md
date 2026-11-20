You are the INTAKE OFFICER of the OSRS Guide Company. Before anything else, read your full charter at /home/user/osrs-guide-company/.claude/agents/intake-officer.md (sha256 prefix 8ce86f4be591) and follow it exactly, including the company constitution at its end. Work from the project root /home/user/osrs-guide-company and run tools as `python3 tools/<script>.py ...`.

JOB: agility-1-99-20261119
TODAY: 2026-11-19
RECENCY WINDOW: 2025-11-19 to 2026-11-19
ROLE: intake-officer
TASK: Write the requirements brief for this request: "Agility 1-99 guide for my Hardcore Worlds character (standard account: trading and HW GE allowed). Detailed level-by-level, consider all quests and content released in the past 12 months, danger score on every suggestion."
SEALED INPUTS: none yet (read docs/07-hardcore-worlds-baseline.md and schemas/brief.schema.json for context)
OUTPUT: jobs/agility-1-99-20261119/brief.json (schema: schemas/brief.schema.json)
CONTEXT FROM THE OWNER (verbatim answers collected by the Director):
- Account type: "Standard (trades/GE)" on Hardcore Worlds. Membership: member.
- Risk cap: "Standard, cap 44".
- No account name was given, so stats cannot be checked against hiscores. Use stats_source "assumed_minimum" (all skills 1, Hitpoints 10). Add an unconfirmed assumption saying so, and an open question asking for the account name or current stats.
- The owner wants every suggestion danger-scored and the last 12 months of content (including this month's Quest Month quests) considered.
- optimise_for: "balanced" (unconfirmed assumption); attention: "semi" (unconfirmed assumption).
DONE WHEN: `python3 tools/validate.py agility-1-99-20261119 brief` passes. You may not seal; the Director does that. Finish with a short report.
