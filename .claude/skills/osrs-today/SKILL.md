---
name: osrs-today
description: Daily check-in for the OSRS Companion. Pulls the owner's Hardcore Worlds hiscores, shows progress since the last visit and the Defence-cap status, lists new game updates, and says where they are in each active guide, with the next decision point and its options. Cheap: tools only, agents only when something needs research. Use as "/osrs-today" (default rsn from profiles/).
---

# /osrs-today: daily companion check-in

Owner: **$ARGUMENTS** (default: the only profile in `profiles/`)

1. Run `python3 tools/companion.py today <rsn>`. It updates the profile snapshot and prints the briefing.
2. Relay it in a few short lines: progress since the last visit, the build check (Defence cap), and anything new in the game.
3. Give **where you are now** and the **next decision**, with its options and danger scores, and ask which way they want to go if a decision is close.
4. Escalate only when needed:
   - New game updates that may touch an active guide: offer `/osrs-refresh <job>`.
   - A finished guide, or a new goal: offer `/osrs-guide <request>`. Intake reads `profiles/<rsn>.json`, so it doesn't re-ask known facts.
   - A level or quest that changes a guide's assumptions (e.g. HP rising enough to re-rate vetoed content): offer a refresh.
5. Do not dispatch agents for a routine check-in.
