# 02: Organisation chart

```
                                 OWNER (you)
                 accepts risk · answers questions · final authority
                                     │
                     ┌───────────────┴────────────────┐
                     │      DIRECTOR (main session)    │  routes work, keeps the ledger,
                     │  authors nothing · can't veto   │  enforces gates, asks the owner
                     └───────────────┬────────────────┘
      ┌──────────────┬───────────────┼────────────────┬─────────────────┬──────────────┐
  CLIENT DESK   INTELLIGENCE      VERIFICATION      STRATEGY         SAFETY          PRODUCTION
  Intake        Patch Sentinel    Fact Verifier     Route Strategist  Risk Officer    Guide Author
  Officer       Methods Analyst   (independent)     Quant             (veto)          Experience
                Quest Archivist                                       Red Team        Designer
                Threat Analyst
                Logistics Analyst
                                                                                     RELEASE ASSURANCE
                                                                                     QA Auditor (veto, signs)
        ─────────────── OBSERVER (not an agent): Sentry hook, logs and polices every tool call ───────────────
```

## Roles at a glance

| Role | Mandate | Produces | Web | Runs | Model |
|---|---|---|---|---|---|
| **Director** | Route, record, enforce gates, ask the owner | dispatch/*.md, ledger events | no | ledger, xp, assemble, render, validate, audit | session |
| **Intake Officer** | Turn the request into a testable brief; verify stats | brief.json | no | hiscores, xp | sonnet |
| **Patch Sentinel** | Sweep the last 12 months of updates (and the next 30 days) | research/updates.json | yes | wiki | opus |
| **Methods Analyst** | Every training method, requirement and rate | research/claims-methods.json | yes | wiki, xp | sonnet |
| **Quest Archivist** | Quest XP, lamps, unlocks, prerequisite chains, quest fights | research/claims-quests.json | yes | wiki | sonnet |
| **Threat Analyst** | Everything that can kill: max hits, aggression, escape, PvP, DC, death rules | research/claims-threats.json | yes | wiki | opus |
| **Logistics Analyst** | Supplies, Hardcore Worlds GE, travel and teleports | research/claims-logistics.json | yes | wiki | sonnet |
| **Fact Verifier** | Independently re-derive and adjudicate every claim | facts.json | yes | wiki, xp, validate | opus |
| **Route Strategist** | Level-by-level routes from verified facts only | plan.json | **no** | xp | opus |
| **Quant** | Sanity-check the deterministic XP engine's output | calc-review.json | **no** | xp, validate | sonnet |
| **Risk Officer** | 8-factor danger ratings with evidence; mitigations; veto | risk.json | **no** | danger, xp | opus |
| **Red Team** | Try to kill the player through the guide | redteam.json | yes | wiki, danger, xp | opus |
| **Guide Author** | Player-facing prose; adds no facts or numbers | prose.json | **no** | — | sonnet |
| **Experience Designer** | The HTML shell; presentation only | templates/guide.html | **no** | render, browser check | sonnet |
| **QA Auditor** | Final independent gate; spot-checks live; signs | qa.json + ledger signature | yes | validate, ledger, audit, wiki, browser check | opus |

The opus model goes to the roles where an error is most likely to cost a life or go unnoticed: recency, threats, verification, strategy, risk, red team and QA.

## Why these roles exist
- **Recency gets its own desk.** The other researchers are expert in the game *as they know it*. The Patch Sentinel's whole job is to know what changed in the last 12 months (Sailing, the 2026 quests, Quest Month, the Hardcore Worlds rules), so new content can't slip through.
- **Threats are separate from methods.** A methods expert is rewarded for finding fast XP, so the hazards are researched by someone whose only job is to find what kills.
- **Verification is independent of research.** The verifier re-fetches every source itself and cannot reuse the researcher's quote.
- **Planners have no web access.** The Strategist, Quant, Risk Officer and Author can only use verified facts. Missing information becomes a logged RFI, not an improvised guess.
- **Two safety roles.** The Risk Officer *scores* systematically, and the Red Team *attacks* creatively. They catch different failures.
- **The arithmetic is code, not an agent.** The Quant reviews the output of `tools/xp.py` rather than doing maths, so XP tables, action counts and totals come out the same every time.
- **The QA Auditor authored nothing.** The ledger refuses a release signature from anyone who sealed content in the job.

## RACI per stage (R = does it, A = accountable, C = consulted, I = informed)

| Stage | Dir | Intake | Research ×5 | Verifier | Strategist | Quant | Risk | Red Team | Author | Designer | QA | Owner |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Brief | A | R | | | | | | | | | | C |
| Research | A | | R | | | | | | | | | I |
| Verification | A | | C (RFI) | R | | | | | | | | |
| Plan | A | | | C | R | C | | | | | | |
| Calculation | R (runs tool) | | | | C | A | | | | | | |
| Danger | A | | | C | C | | R (veto) | | | | | C (accepts) |
| Red team | A | | C | C | C | | C | R | | | | C (accepts) |
| Prose | A | | | | | | C | | R | | | |
| Presentation | A | | | | | | | | | R | | |
| Release | I | | | | | | | | | | R/A (veto) | I |
