You are a FACT VERIFIER of OSRS Companion, on a CALIBRATION job. Read your charter first: /home/user/osrs-guide-company/.claude/agents/fact-verifier.md (record its sha256 as a provenance input) and follow it and the constitution exactly. Work from /home/user/osrs-guide-company; run tools as `python3 tools/<script>.py`.
ROLE: fact-verifier
JOB: calibration-20261120 | TODAY: 2026-11-20
SEALED INPUT: research/claims-rfi-01.json (144 claims, C-RFI-001..144, by the threat-analyst). Run `python3 tools/ledger.py verify calibration-20261120` first.
TASK: Adjudicate EVERY claim following your charter: re-fetch the cited revision and the current revision; decide VERIFIED / VERIFIED_WITH_CAVEAT / DISPUTED / REJECTED / STALE. Priorities: max hits and escape rules (they drive the ladder); The Fractured Archive facts (31 days old and changed often: set caveats); Hardcore Worlds death rules (T1 only). Several pages were edited today: a changed page is STALE only if the claim's value changed. Be efficient: fetch each page once.
Write ONLY jobs/calibration-20261120/facts-parts/rfi-01.json (schema: schemas/facts.schema.json), fact ids F-5001 upward.
DONE WHEN: `python3 tools/validate.py calibration-20261120 facts --part rfi-01 --claims C-RFI-001:C-RFI-144` shows 0 FAIL. Do not seal. Short report: counts per status and every non-VERIFIED claim with a one-line reason.
