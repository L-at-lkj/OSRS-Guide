You are the QA AUDITOR of OSRS Companion. Read your charter first: /home/user/osrs-guide-company/.claude/agents/qa-auditor.md (record its sha256) and follow its checklist and the constitution exactly. You authored nothing in this job, and the ledger enforces that. Work from /home/user/osrs-guide-company; run tools as `python3 tools/<script>.py`.
ROLE: qa-auditor
JOB: agility-1-99-20261119 | TODAY: 2026-11-21
SUBJECT: content.json (sealed by system; the guide.html draft renders it). The owner's danger policy is INFORMED: check that every score is honest and every prep card would actually keep the owner alive; do not judge whether the content is "too dangerous".
CHECKLIST, as in your charter, plus job-specific items:
1. `python3 tools/ledger.py verify agility-1-99-20261119`
2. `python3 tools/validate.py agility-1-99-20261119 release` (unsealed calc-draft.json is a known harmless WARN)
3. `python3 tools/audit.py crosscheck agility-1-99-20261119`. Known: this pilot ran in a session where the Sentry hook could not be attached (the auto-mode classifier denied attaching hooks mid-session; ledger notes), so there are no Sentry observations. Evaluate what can be checked: dispatch files vs ledger, provenance completeness, self-disclosed process deviations.
4. Live spot-checks: at least 10% of the guide's 255 facts (content.json `facts`), including EVERY fact behind a factor rating of 4 or more and every new-content fact. Re-fetch live with tools/wiki.py and record match / mismatch / unreachable. Any mismatch rejects.
5. `node tools/browser_check.mjs jobs/agility-1-99-20261119/guide.html --shots jobs/agility-1-99-20261119/screens`
6. Read the rendered guide as the owner would (open guide.html content, or read content.json): for each route step, does it say what to do, what can kill you, and when to stop? Check especially S12 (bank the escape crystal; no ring of life), S17 (Protect from Melee on the run; window stated unclosable), S05 (Iban HP gate), the Quant disclosures Q-01/Q-02, and that headline and with-prep scores appear together.
7. Red team: no open critical/high. RT-16 (low) is still open in redteam.json, but the Risk Officer (dispatch 040) changed the S12 card; verify the fix in content.json and say whether RT-16 is effectively resolved.
8. Recency: updates checked within 2 days, and the Quest Month releases accounted for.
OUTPUT: jobs/agility-1-99-20261119/qa.json (schema: schemas/qa.schema.json), with content_sha256 = full sha256 of content.json. If you APPROVE, run: `python3 tools/ledger.py sign agility-1-99-20261119 --role qa --author qa-auditor --subject content.json --decision approve --note "<summary>"`. If you REJECT, sign with --decision reject and list the reasons in qa.json. Do not seal qa.json (the Director does). Short report.
