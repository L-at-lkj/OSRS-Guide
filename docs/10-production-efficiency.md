# 10: Production efficiency (owner feedback, 2026-11-22)

The owner asked for a more efficient production approach, with the Red Team used only at planned stages. The Agility pilot used about 45 agent runs and hit the usage limit 6 times. The target is **about 12–15 runs per skill guide** with no loss of minimal-trust controls.

## Rules
| # | Rule | Saves |
|---|---|---|
| 1 | **Brief from profile.** Use `tools/brief.py` (system-sealed). Dispatch the intake agent only for a new account or a missing fact. | 1–4 runs |
| 2 | **Fact carry-over.** `tools/carryover.py` reuses facts verified in earlier jobs whose wiki revision is unchanged (checked live). Desks research only what's new. | 30–60% of research and verification |
| 3 | **Shared update sweep.** Run the Patch Sentinel at most once a day company-wide (`/osrs-today` notes new updates). A job only triages what affects its subject. | 1 heavy run per job |
| 4 | **Three research desks** for skill guides: methods (which also covers logistics and profit), quests, threats. The logistics desk is dispatched only for supply-heavy skills. | 1–2 runs |
| 5 | **One verifier per research file**, run in parallel. Carried facts skip verification. | — |
| 6 | **One RFI round, batched.** Everything still unknown after it is rated conservatively by the Risk Officer. | 3–6 runs |
| 7 | **Red Team once per job**, at a planned stage (after plan + calc + risk). Fixes are confirmed by **QA**, not by a second Red Team run. A second Red Team run happens only if a fix moves a step's danger by a tier or more. | 2–3 runs |
| 8 | **One strategist revision.** All risk vetoes, Red Team findings and QA text fixes are batched into a single revision. | 2–3 runs |
| 9 | **Quant only when the plan's numbers change** (numeric hash). Text edits never re-trigger it. | 1–2 runs |
| 10 | **Mechanical work stays in code.** Prices (`tools/prices.py`), brief, carry-over, calculation, danger, assembly and render. | — |
| 11 | **Model routing.** Opus for judgement-heavy or safety roles; Sonnet for mechanical or writing roles (table below). | about 40% of cost |
| 12 | **At most 3 agents in parallel.** Seal and commit after every return, so a usage-limit stop loses nothing; resume stopped agents with SendMessage. | lost work |

## Model routing
| Opus | Sonnet |
|---|---|
| threat-analyst, fact-verifier (threats and quests), route-strategist, risk-officer, red-team, qa-auditor | methods-analyst, quest-archivist, logistics-analyst, fact-verifier (methods and logistics), quant, guide-author, experience-designer, intake-officer, patch-sentinel (triage) |

## Planned pipeline for a skill guide (≈12–15 runs)
1. `brief.py`, `carryover.py`, `prices.py` (0 runs)
2. Research: methods+profit, quests, threats in parallel (3)
3. Verification, one per file, in parallel (3)
4. One batched RFI round, only if needed (0–2)
5. Strategist (1), then `xp.py`, then Quant (1)
6. Risk Officer (1)
7. **Red Team, once** (1)
8. One strategist and risk revision, only if findings need it (0–2)
9. Guide Author (1)
10. Assemble and render, then **QA** (1), which also confirms the Red Team fixes. A rejection triggers one fix round, then a QA re-check of the failures only.

## Style rules (enforced by validate.py)
- Dot points everywhere: intro and outro are arrays of points. Word limits: summary 25, instruction 30, tip 25, warning 35.
- Plain, neutral tone. Lecturing phrases ("obviously", "simply", "of course", "needless to say") raise a warning.
- Exception: a section that is read out automatically (narration) may be prose.
- Danger: every step at 45 or more without prep gets a bright-red border and a red banner.
