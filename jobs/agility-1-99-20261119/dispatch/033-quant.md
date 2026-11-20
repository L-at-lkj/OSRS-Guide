You are the QUANT of OSRS Companion. Your charter: /home/user/osrs-guide-company/.claude/agents/quant.md (record its sha256). Follow it and the constitution exactly. No web access. Work from /home/user/osrs-guide-company.
ROLE: quant
JOB: agility-1-99-20261119 | TODAY: 2026-11-20
TASK: Re-review calc.json after plan revision 032. Sealed inputs: plan.json (1fd8d37ca65e), calc.json (660fe306d6f2), facts.json (70fcb7eed3ab), and your previous review (calc-review.json, unsealed for this update). Routes are now safest (228.2 h) and balanced (222.86 h); fastest was removed, along with steps S22, S23 and S24. Confirm the remaining step numbers are unchanged from the previous review (it found none of its arithmetic changed), re-check the Defence cap (end levels), and carry forward the disclosures Q-01 (totals exclude quest time) and Q-02 (balanced vs safest gap). Keep it brief.
OUTPUT: jobs/agility-1-99-20261119/calc-review.json with calc_sha256 = the full sha256 of calc.json. Do not seal.
DONE WHEN: `python3 tools/validate.py agility-1-99-20261119 calc` shows 0 FAIL. Short report.
