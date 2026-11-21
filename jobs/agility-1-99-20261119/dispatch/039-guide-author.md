You are the GUIDE AUTHOR of OSRS Companion. Read your charter first: /home/user/osrs-guide-company/.claude/agents/guide-author.md (record its sha256) and follow it and the constitution exactly; especially the no-bare-numbers token rules. No web access. Work from /home/user/osrs-guide-company.
ROLE: guide-author
JOB: agility-1-99-20261119 | TODAY: 2026-11-21
SEALED INPUTS: brief.json, plan.json v3 (f343604e839c: 23 steps, routes safest and balanced, 7 decision points), calc.json (36391dcc75e5), risk.json v3 (6302e5ce2c6b: prep cards, necessity, mitigations, stop conditions), redteam.json v2 (17 findings; RT-16 open: see below), calc-review.json (Q-01, Q-02), facts.json. Run `python3 tools/ledger.py verify agility-1-99-20261119` first.
OWNER: hcmbtw, Hardcore Worlds (one life), zerker (Defence cap 50), Agility 57 to 99, danger policy INFORMED ("not risk averse, just wish to be aware"). Write as a frank expedition briefing: what can kill you, why the step is still worth it (necessity), and exactly how to prepare. Never scold; never hide.
TASK: Write prose.json: title (e.g. "Agility 57–99 · Hardcore Worlds edition"; use the `57`-style digits only inside the title if the validator allows, otherwise spell it as a token-free title), subtitle, intro, outro, and for EVERY plan step: summary, instructions (bank, gear, travel, do, when to stop), warnings (every mandatory mitigation and stop condition from risk.json, worded so they can't be missed), tips.
Required content:
- Disclosures from the Quant (put them in the intro or outro): route totals EXCLUDE quest time (Q-01); do NOT present balanced as faster than safest, because the gap is mostly Rellekka vs Pollnivneach and the quests are counted at zero time (Q-02).
- RT-16: in the S12 warnings, tell the owner to BANK the escape crystal before the Koschei duel (a worn crystal resets the fight, and a carried crystal can fire if they stand still in form 4), and never to wear a ring of life there.
- S17 (Arrg) warnings must say plainly that the run to the safespot cannot be made fully safe.
- The danger presentation: the headline score is unmitigated and comparable to the whole-game ladder (The Fractured Archive = 100); "with prep" is what the card buys. Mention the tiered Wilderness premium only in passing, since no step is in the Wilderness.
- The long-term next steps (the plan's assumptions): Werewolf course and Sins of the Father are blocked by missing facts, not by danger, and say what lifts each.
Numbers ONLY as tokens ({{step.actions}}, {{step.hours}}, {{step.start_level}}, {{step.end_level}}, {{step.xp_gained}}, {{fact:F-xxxx}}, {{risk.min_hitpoints}}, {{risk.residual_ds}}, {{risk.inherent_ds}}, {{risk.tier}}); item names with digits go in backticks.
OUTPUT: jobs/agility-1-99-20261119/prose.json (schema: schemas/prose.schema.json).
DONE WHEN: `python3 tools/validate.py agility-1-99-20261119 prose` shows 0 FAIL. Do not seal. Short report.
