# 04: Production pipeline

```
 request ─► [0 open job] ─► [1 INTAKE] ─► owner Q&A ─► [2 RESEARCH ×5 in parallel] ─► [3 VERIFY] ◄─┐
                                                                                         │  RFI loop │
                                                                                         ▼  (≤3)  ───┘
              ┌──────────── veto / quant fail ────────────┐
              ▼                                           │
         [4 PLAN] ─► xp.py ─► [4b QUANT] ─► [5 RISK OFFICER] ─► [5b RED TEAM] ─► owner accepts / rejects risks
                                                │ veto                │ critical/high findings → owning role
                                                └──────────►──────────┘
         ─► [6 AUTHOR] ─► assemble.py ─► render.py (DRAFT) ─► [7 QA AUDITOR] ─► sign ─► render (RELEASED)
                                                                    │ reject → owning roles
         ─► audit.py export ─► [8 report to owner]
```

## Stage gates

| Stage | Artifact | Gate (must pass) | Seal author |
|---|---|---|---|
| 1 Intake | brief.json | `validate.py <job> brief` | intake-officer |
| 2 Research | research/*.json | `validate.py <job> research` | each desk |
| 3 Verify | facts.json | `validate.py <job> facts` (every claim adjudicated, independent, T1/T2) | fact-verifier |
| 4 Plan | plan.json | `validate.py <job> plan` (facts-only, numbers match, safest route exists) | route-strategist |
| 4 Calc | calc.json | `xp.py simulate` with no route errors | system |
| 4b Quant | calc-review.json | `validate.py <job> calc` (plan hash matches; decision pass) | quant |
| 5 Risk | risk.json | `validate.py <job> risk` (every step rated; evidence; cap; no veto) | risk-officer |
| 5b Red team | redteam.json | `validate.py <job> redteam` (no open critical/high) | red-team |
| 6 Prose | prose.json | `validate.py <job> prose` (every step; no bare numbers) | guide-author |
| 6 Content | content.json | `assemble.py` refuses unsealed or changed inputs | system |
| 6 HTML | guide.html | `validate.py <job> html` (embedded data identical; no external scripts) | system |
| 7 QA | qa.json + signature | `validate.py <job> release`, crosscheck, spot-checks, browser check | qa-auditor |
| 8 Audit | audit.json / audit.html | `audit.py export` | system |

## Loops and escalation
- **Revisions** always go *unseal (logged reason) → owning role fixes → gate → reseal*. Downstream artifacts built on the old version then fail their hash checks and must be rebuilt. The pipeline cannot silently keep stale work.
- **RFI loop** (missing facts): at most 3 rounds, then the gap goes to the owner.
- **Conflicts between agents** (e.g. the strategist disputes a risk rating): the Director doesn't arbitrate on substance. It puts both positions to the owner, or sends the dispute to the role that owns the decision (the Risk Officer owns danger, the Verifier owns facts).
- **Risk acceptance**: only the owner, recorded verbatim against the step id.

## Parallelism
- The five research desks run in parallel (one message, five Agent calls).
- The Risk Officer and Quant could run in parallel after the plan, but the Risk Officer needs calc.json to know the player's level at each step, so they run in sequence by default.
- The Red Team runs after risk, so it can attack the mitigations as well as the plan.
