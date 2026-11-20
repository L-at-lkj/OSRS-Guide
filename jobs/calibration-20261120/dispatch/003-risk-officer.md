You are the CHIEF RISK OFFICER of OSRS Companion. Read your charter first: /home/user/osrs-guide-company/.claude/agents/risk-officer.md (sha256 prefix 4b97db385eb0; it was updated for the owner's new "informed" danger policy, so read the "Game-relative scale and necessity" and "Verdicts" sections carefully) and docs/05-danger-model.md (sections 1-7). Follow them and the constitution exactly. No web access. Work from /home/user/osrs-guide-company; run tools as `python3 tools/<script>.py`.
ROLE: risk-officer
TODAY: 2026-11-20
OWNER POLICY (verbatim, ledger agility-1-99-20261119 seq 131): "design the danger rating based around all activity in the game with for example, the fractured archives being maximum danger, i am not risk averse just wish to be aware, you cannot avoid much of the dangerous content despite the danger due to crucial upgrades obtained". Ceiling: The Fractured Archive at solo/duo scale = 100 (calibration ledger seq 7).

This dispatch has TWO deliverables, done in this order.

PART 1: CALIBRATION (job calibration-20261120)
Sealed inputs: policy/danger-calibration.json (85c5a87b322d: 27 anchors), jobs/calibration-20261120/facts.json (0e2bbba7d2a3: 144 facts; 77 VERIFIED, 62 CAVEAT, 5 DISPUTED; search with grep).
For EACH anchor, rate the 8 factors for a TYPICAL account that attempts that content, citing facts (lethality/pvp/escape > 0 need fact ids), set the flags, and give a suggested position on the 0-100 ladder with one line of reasoning. The researchers found several original rationales wrong (Colosseum and Inferno are escapable; Wintertodt now drains warmth, not HP; ToA expert starts at 300; the Revenant Caves are singles-plus; the Ape Atoll hazards are unsupported). Correct them. Keep tfa-max at position 100.
Write jobs/calibration-20261120/anchor-ratings.json as {"anchors":[{"id","factors":{8 factors as {"score","rationale","facts"}},"flags":[...],"suggested_position":int,"reasoning":str,"facts":[...]}], "provenance": {...}} using the anchor ids from the policy file. Check the ordering with `python3 tools/danger.py explain`.

PART 2: RE-RATE THE AGILITY GUIDE (job agility-1-99-20261119)
Sealed inputs: brief.json (c27aa6bc9969), facts.json (70fcb7eed3ab), plan.json (6cc4bade59d9: the ORIGINAL 26 steps and 3 routes, restored), calc.json (313257a6f2ab). Your previous risk.json (5e2f34f18337) was unsealed for this revision (ledger seq 133); start from it.
Revise risk.json:
- Set risk_appetite "informed".
- Add `necessity` (class, why, unlocks, safer_alternatives, facts) to EVERY entry.
- Every entry whose model score is 45 or more needs a complete prep card (mitigations, min_hitpoints, stop_conditions, bailout, necessity).
- Re-decide each previous veto (S17 Troll Romance, S23 Werewolf course, S24 Sins of the Father, S25 Hallowed Sepulchre, route `fastest`) under the new rule: danger alone never vetoes; a veto needs a veto_basis (unverifiable_mechanic, insufficient_facts_for_prep, breaks_hard_constraint, dominated_without_benefit). Otherwise use approve_with_conditions with a full prep card. Explain each decision in verdict_reason.
- Keep factor ratings honest; do not lower them. The owner accepted S05, S06, S12 and S16 (ledger seq 123-126).
Check with `python3 tools/danger.py score agility-1-99-20261119` and `python3 tools/validate.py agility-1-99-20261119 risk` (0 FAIL other than vetoes you keep with a veto_basis).

OUTPUT: jobs/calibration-20261120/anchor-ratings.json and jobs/agility-1-99-20261119/risk.json, each with provenance. Do not seal. Short report: the anchor table (id, model score, suggested position), ordering concerns, the revised verdicts for S17/S23/S24/S25/fastest, and anything needing the owner.
