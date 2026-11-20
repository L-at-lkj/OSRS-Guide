---
name: osrs-calibrate
description: Calibration board for the game-relative Gielinor Danger Index. Researches, verifies, rates and orders the reference ladder in policy/danger-calibration.json (The Fractured Archive = 100 down to safe AFK skilling) so every guide's danger scores read against the whole game. Run once before relying on calibrated scores, then quarterly or after major content releases.
---

# /osrs-calibrate: the calibration board

Arguments: **$ARGUMENTS** (optional: anchor ids to (re)calibrate; default all with status `proposed`)

The ladder turns the 8-factor danger model into a game-relative scale. Each **anchor** is a reference activity rated for a *typical account that attempts it*. A guide step is rated for *the owner's* account. So "danger 40" reads as "as dangerous for you as <anchor near 40> is for a typical player doing it".

Use the dispatch protocol from /osrs-guide. Job id: `calibration-<yyyymmdd>`. `ledger.py init` it like any job.

1. **Research** (parallel, split the anchors between up to 2 instances): dispatch **threat-analyst** with the anchor list. For each anchor, the claims cover: typical attempting account (stats and gear); max hits and the deadliest mechanics; instance or escape rules; PvP exposure; Hardcore Worlds death classification; typical duration. Output `research/claims-rfi-NN.json`, desk "rfi".
2. **Verify**: dispatch **fact-verifier** instances; merge with `tools/merge_facts.py`.
3. **Rate**: dispatch **risk-officer** to write `jobs/<cal-job>/anchor-ratings.json`: for each anchor, the 8 factor ratings with evidence, the flags, and a suggested position with reasoning. The Director copies the ratings into `policy/danger-calibration.json` (status `rated`) in governance mode; the file is company policy.
4. **Challenge**: dispatch **red-team** to attack the ordering. Which anchors are out of order, and which are missing? Run `python3 tools/danger.py ladder`: every CONFLICT line must be resolved, either by re-rating or by the board adjusting a position with a written reason.
5. **Approve**: show the owner the ladder (position, activity, model score) with AskUserQuestion. Positions the owner approves become `approved`. The top anchor must stay The Fractured Archive (hardest mode) = 100 unless the owner says otherwise.
6. Bump `version`, commit, and record a `decision` in the calibration job's ledger. Guides rendered after this show calibrated scores. Older guides are re-scored by /osrs-refresh.
