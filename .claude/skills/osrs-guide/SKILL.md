---
name: osrs-guide
description: Director's runbook. Produce an audited, danger-scored interactive OSRS Hardcore Worlds guide (e.g. "/osrs-guide Agility 1-99") by running the full company pipeline - intake, parallel research, independent verification, planning, deterministic calculation, risk and red-team review, writing, assembly, QA release and audit export.
---

# /osrs-guide: Director's runbook

Request: **$ARGUMENTS**

You are the Director (see CLAUDE.md). Follow the stages below in order. Every gate is a command that must pass. Throughout, give the owner short progress lines, e.g. "Research desks dispatched (5)", or "Verifier: 74 verified, 3 disputed, 1 rejected".

## Dispatch protocol (use for EVERY agent call)
1. Choose `NNN` = next number in `jobs/<job>/dispatch/` (001, 002...).
2. **Write** the prompt to `jobs/<job>/dispatch/NNN-<agent>.md` using the template below.
3. `python3 tools/ledger.py seal <job> dispatch/NNN-<agent>.md --author director`
4. `python3 tools/ledger.py record <job> --event dispatch --author director --ref dispatch/NNN-<agent>.md --note "<agent>: <purpose>"`
5. Call the Agent tool with `subagent_type: <agent>` and `prompt:` **byte-for-byte the file's text**. Parallel dispatches go in one message.
6. On return: `python3 tools/ledger.py record <job> --event return --author director --note "<agent>: <one-line outcome>"`. Run the stage gate, then seal the artifact with `--author <agent>`.

Dispatch template:
```
JOB: <job>
TODAY: <YYYY-MM-DD>
RECENCY WINDOW: <from> to <to>
ROLE: <agent>
TASK: <what to do, specific to this job>
SEALED INPUTS: <path> (sha256 <first 12 chars>) ...
OUTPUT: jobs/<job>/<path> (schema: schemas/<name>.schema.json)
CONTEXT FROM THE OWNER: <verbatim answers relevant to this role, or "none">
DONE WHEN: <the gate command that must pass>
```

## Stage 0: open the job
- Job id: `<subject>-<from>-<to>-<yyyymmdd>`, lowercase with hyphens (e.g. `agility-1-99-20261119`).
- `python3 tools/ledger.py init <job> --request "<verbatim request>"` (this also makes it the active job that Sentry tags).

## Stage 1: intake → brief.json
- Dispatch **intake-officer**. Gate: `python3 tools/validate.py <job> brief`.
- If the brief has `open_questions` or unconfirmed assumptions that would change the guide, ask the owner (AskUserQuestion, at most 4 questions per call, recommended option first). Record each answer: `ledger.py record --event decision --author director --note "Q: ... A: ..."`. If an answer changes the brief, unseal it with a reason and re-dispatch intake with the answers.
- Seal: `ledger.py seal <job> brief.json --author intake-officer`.

## Stage 2: research (5 desks in parallel, one message)
- Dispatch **patch-sentinel**, **methods-analyst**, **quest-archivist**, **threat-analyst** and **logistics-analyst**. Each gets the sealed brief and its output path under `research/`.
- Gate: `python3 tools/validate.py <job> research`. FAIL lines are fixed by the owning desk: re-dispatch with the exact FAIL text. WARN lines are recorded.
- Seal each research file with its desk's role.

## Stage 3: verification → facts.json
- Dispatch **fact-verifier** with all the sealed research files. For big jobs (over 100 claims), dispatch **one verifier instance per desk in parallel**. Each writes `facts-parts/<desk>.json` within its fact-id range (updates 0001-0199, methods 0200-0399, quests 0400-0599, threats 0600-0799, logistics 0800-0899, rfi 0900-0999). Seal each part with `--author fact-verifier`, then run `python3 tools/merge_facts.py <job>` and seal facts.json with `--author system`.
- Gate: `python3 tools/validate.py <job> facts`. Seal with `--author fact-verifier` (single instance) or `system` (merged).
- **RFI loop:** for each `rfi` entry, dispatch the named desk to write `research/claims-rfi-NN.json`, seal it, then unseal facts.json ("adjudicate RFI NN") and re-dispatch the verifier to add the new facts. Allow at most 3 loops, then report the gap to the owner.

## Stage 4: plan and numbers
- Dispatch **route-strategist** with brief, updates and facts. Gate: `validate.py <job> plan`. Seal with `--author route-strategist`.
- Run `python3 tools/xp.py simulate <job>` and seal calc.json with `--author system`.
- Dispatch **quant**. Gate: `validate.py <job> calc`. Seal calc-review.json with `--author quant`.
- If the quant fails it: unseal plan.json (the reason quotes the finding), re-dispatch the strategist, then re-run the calc and the quant.

## Stage 5: safety
- Dispatch **risk-officer** with brief, facts, plan and calc. Gate: `validate.py <job> risk`. Seal with `--author risk-officer`.
  - A **veto** goes back to the strategist (unseal plan, give the veto reason verbatim), then repeat Stage 4 and the risk review.
  - A step above the cap on the safest route with no alternative, or any Critical residual: ask the owner. Show the step, raw and residual DS, hazards, mandatory mitigations, the bail-out plan and the safer alternative (if any). Record a yes as `ledger.py record <job> --event accept_risk --author user --ref <step_id> --note "<verbatim question and answer>"`. A no goes back to the strategist.
- Dispatch **red-team** with everything sealed so far. Gate: `validate.py <job> redteam`.
  - For each open critical or high finding, route it to the role that owns the fix (strategist, risk-officer or fact-verifier, via RFI). Re-run their gates, then unseal redteam.json and re-dispatch red-team to re-test and update statuses. Only red-team changes a finding's status. Risks the owner accepts are recorded with `accept_risk`.
  - Seal redteam.json with `--author red-team` once no critical or high findings are open.

## Stage 6: production
- Dispatch **guide-author**. Gate: `validate.py <job> prose`. Seal with `--author guide-author`.
- `python3 tools/assemble.py <job>`, then seal content.json with `--author system`.
- `python3 tools/render.py <job>` (a DRAFT banner is expected), then `validate.py <job> html`.
- Optional: dispatch **experience-designer** if the browser check or the owner raises presentation issues.

## Stage 7: release
- Dispatch **qa-auditor**. It writes qa.json and signs the ledger itself. Seal qa.json with `--author qa-auditor`.
- If approved: `python3 tools/render.py <job>` (now RELEASED), `validate.py <job> release`, then seal guide.html with `--author system`.
- `python3 tools/audit.py export <job>`, then seal audit.json and audit.html with `--author system`.
- If rejected: route each reason to its owner, repeat the affected stages, then go back to QA.

## Stage 8: report to the owner
Give a short summary covering:
- the guide path (`jobs/<job>/guide.html`) and audit path (`jobs/<job>/audit.html`);
- route totals, worst residual danger per route, accepted risks;
- new-content highlights from the recency window;
- anything left unverified or caveated.

Offer to publish the guide as a private artifact page so it can be opened on a phone.
