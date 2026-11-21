You are the ROUTE STRATEGIST of OSRS Companion. Your charter: /home/user/osrs-guide-company/.claude/agents/route-strategist.md (record its sha256). No web access. Work from /home/user/osrs-guide-company.
ROLE: route-strategist
JOB: agility-1-99-20261119 | TODAY: 2026-11-21
TASK: TEXT-ONLY corrections to plan.json (unsealed for you). Change NO numbers, step ids, routes, requirements, xp fields or facts. The Risk Officer's revised risk.json (sealed) found plan text that is now wrong or unsafe:
1. DP03 option C (Troll Romance): its pros say "Protect from Missiles before talking to Arrg". That is WRONG: Arrg's primary attack is a 38 melee, so the card uses Protect from Melee on the run and Protect from Missiles only at the safespot. Fix it, and add to its cons: "the run to the safespot cannot be made fully safe (two hits can kill at 48 HP; it partly depends on hit RNG)". The owner re-confirmed keeping this option (ledger accept_risk, informed).
2. S19: its lamp choices must show Defence explicitly with "never (zerker cap)".
3. DP07 option B: note that the long-term Sins of the Father chain adds 4,600 forced Defence XP (Defence about 24 with The Fremennik Trials; cap 50).
4. Random events assumption or texts: replace any "events can attack" wording with "dismiss random events in dangerous areas; never accept a teleporting event there".
5. S12 texts: no ring of life at Koschei, and do not wear the escape crystal in the duel (it would reset the fight). The owner re-confirmed S12 on the corrected card.
Check that `python3 tools/xp.py simulate agility-1-99-20261119 --out calc-draft.json` gives the same totals as before (safest 228.2 h, balanced 222.86 h) and that `python3 tools/validate.py agility-1-99-20261119 plan` shows 0 FAIL. Update provenance. Do not seal. Short report.
