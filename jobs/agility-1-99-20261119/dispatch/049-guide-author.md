You are the GUIDE AUTHOR of OSRS Companion. Re-read your charter: /home/user/osrs-guide-company/.claude/agents/guide-author.md (updated with the owner's STYLE rules; record its sha256). No web access. Work from /home/user/osrs-guide-company.
JOB: agility-1-99-20261119 | TODAY: 2026-11-22
OWNER FEEDBACK (verbatim): "avoid large slabs of text avoid the arrogant tone, stick to point in tips unless a section is read out automatically dot points shoulkd be used. the high danger tasks should be much clearer (bright red for example). ensure profit is considered as part of the advice provided."
TASK: Rewrite prose.json (unsealed for you; keep every safety fact the current version has) to the new style:
- `intro` and `outro` become ARRAYS of short dot points (at most 6 each). Keep the Quant disclosures (route hours exclude quest time; Balanced isn't faster) and the danger-scale explanation (headline is without prep; "with prep" is what the card buys; The Fractured Archive = 100), each as one short point.
- Every step: summary of 25 words or fewer; instructions of 30 words or fewer each; tips of 25 or fewer, stating the point only; warnings of 35 or fewer. Keep every mandatory mitigation and stop condition from risk.json as its own warning point (S12: bank the escape crystal, no ring of life; S17: Protect from Melee on the run, run window unclosable; S05: Iban HP gate).
- Plain, neutral tone. No lecturing, no "Danger first:" preambles. The red banner now does that job in the template.
- Profit: on each rooftop step add one tip such as "Profit: about {{step.hours}} of laps; marks sell as amylase crystals on the Hardcore Worlds GE". Use tokens; never write gp numbers (the template shows profit in the step stats).
- Numbers ONLY as tokens; item names with digits go in backticks.
DONE WHEN `python3 tools/validate.py agility-1-99-20261119 prose` shows 0 FAIL (it now enforces word limits and flags lecturing phrases). Update provenance. Do not seal. Short report.
