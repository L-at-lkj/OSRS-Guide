You are the CHIEF RISK OFFICER of OSRS Companion. Your charter: /home/user/osrs-guide-company/.claude/agents/risk-officer.md (sha256 prefix 7cf277720b6e; record it). Follow it and the constitution exactly. No web access. Work from /home/user/osrs-guide-company.
ROLE: risk-officer
JOB: agility-1-99-20261119 | TODAY: 2026-11-20 | appetite: informed
TASK: Revise risk.json (unsealed for you) to resolve the Red Team's findings in the sealed redteam.json (c70e15dbfd18) and re-base it on the CURRENT sealed plan.json (1fd8d37ca65e: 23 steps; S22, S23 and S24 removed; routes safest and balanced; 7 decision points), calc.json (660fe306d6f2) and facts.json (70fcb7eed3ab). Keep entries for removed steps only if they are useful history; the validator treats them as honoured.
Fix the prep cards, using verified facts only:
- RT-01 S17 Arrg: Protect from Melee is the right prayer for his primary melee (max 38). Correct "eat at 30" to an eat threshold that survives the worst two-hit sequence. Give a minimum heal per food and a combo-eat rule if the facts support it; if the window cannot be closed, say so plainly in the card.
- RT-02 S12 Koschei: REMOVE the ring of life (the cited wiki says it resets the fight to form 1, so the quest can never be finished). Remove its escape credit and re-score. Write the honest card for forms 1-3 (run-ending on Hardcore Worlds).
- RT-08 S05: add an HP gate and a stop rule for Iban's temple red spikes (5-8 each, fast, through prayer, stun).
- RT-09 S12: the first Rellekka trip is on the Camelot road, which is unresearched. Rate its travel conservatively and say what to watch for.
- RT-10: unpublished rooftop fail damage (Seers' and Ardougne, about 128 h). Do not claim "a fail cannot exceed current HP" without a source. State the eat threshold as a conservative rule.
- RT-11: say whether, where and how the free escape crystal helps (disconnect cover where it works; unknown in instances; does not fire while moving).
- RT-12: random events: the real risk is accepting a teleporting event in a dangerous area. Say to dismiss events there.
- RT-13: note the long-term Sins of the Father chain's 4,600 forced Defence XP (Defence would reach about 24 with The Fremennik Trials, still under 50), and that S19's lamp must never go to Defence.
- RT-14: everything is now rated against the current plan/calc and the current engine. Preview with `python3 tools/danger.py score agility-1-99-20261119`. Note that the published headline is now the UNMITIGATED game-relative score (like-for-like with the ladder) and "with prep" is the residual; flag floors now apply after calibration.
Keep factor ratings honest (raise them where a fix exposes more danger, e.g. S12 without the ring). Update verdict_reason texts so they quote no stale numbers. Every step whose headline is 45 or more needs a complete prep card.
DONE WHEN: `python3 tools/validate.py agility-1-99-20261119 risk` shows 0 FAIL. Do not seal. Short report: the new score table (headline / with prep / comparable to), what changed per RT finding, and anything the owner must re-accept (S12's card changed materially).
