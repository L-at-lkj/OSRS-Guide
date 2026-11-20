# 03: Minimal-trust model

**Premise:** any agent can be wrong, overconfident, out of date, misled by a web page (prompt injection), or lazy. No single agent can push a wrong or dangerous recommendation into a released guide on its own say-so.

## Controls

| # | Control | Type | Where it's enforced |
|---|---|---|---|
| 1 | **Tool allowlists per role** (e.g. planners have no web; the author has no web and no scripts) | Preventive | `tools:` frontmatter in `.claude/agents/*.md`, plus Sentry's per-role checks |
| 2 | **Write scopes per role**: each role writes only its own artifact | Preventive | Sentry `WRITE_SCOPE` |
| 3 | **Sealed handoffs**: SHA-256 in a hash-chained ledger; a sealed file is write-protected and any later change is detected | Preventive + detective | `tools/ledger.py`, Sentry |
| 4 | **Separation of duties** on sealing: only the owning role may seal its artifact; calc, content and html can only be sealed by `system` | Preventive | `ledger.py SEAL_RIGHTS` |
| 5 | **Independent verification**: the verifier re-fetches every source; dates must postdate the research seal; values must match exactly or the fact is DISPUTED | Detective | fact-verifier, `validate.py facts` |
| 6 | **Facts-only planning**: plan numbers must equal verified fact values | Preventive | `validate.py plan` |
| 7 | **Deterministic computation**: XP and danger maths come from code | Preventive | `xp.py`, `danger.py`, `assemble.py`, `render.py` |
| 8 | **No bare numbers in prose**: the author can only reference calculated or verified values | Preventive | `validate.py prose` |
| 9 | **Renderer can't alter content**: embedded data must equal content.json | Detective | `validate.py html` |
| 10 | **Vetoes**: risk officer, fact verifier, QA and owner; the Director can't override | Preventive | ledger `veto` events, gates |
| 11 | **Owner-only risk acceptance**, recorded verbatim | Preventive | `ledger.py record --event accept_risk` (author `user` only) |
| 12 | **QA independence**: no content author can sign the release | Preventive | `ledger.py sign` |
| 13 | **Release bound to exact content**: the approval is for one content hash; any change revokes it | Preventive | `ledger.py released`, `render.py` banner |
| 14 | **Independent observation**: Sentry logs every tool call by every agent to a hash-chained, append-only log | Detective | `tools/sentry.py` hook |
| 15 | **Dispatch transparency**: the Director's exact prompt to each agent is sealed; the audit matches it to the hash of the prompt actually sent | Detective | `audit.py crosscheck` |
| 16 | **Provenance vs observation**: each agent's self-reported actions are compared with Sentry's observations | Detective | `audit.py crosscheck` |
| 17 | **Shell lockdown**: no chaining, substitution, redirection, rm, curl, wget, sudo or git push; interpreters run only `tools/` scripts | Preventive | Sentry `check_bash` |
| 18 | **Governance mode**: changing company policy needs the owner to start Claude with `OSRS_GOVERNANCE_MODE=1`, and is still logged | Preventive | Sentry |
| 19 | **Live spot-checks** at release: at least 10% of facts, including every high-danger and new-content fact | Detective | qa-auditor |
| 20 | **Prompt-injection hygiene**: fetched content is data, never instructions (in every agent's constitution) | Preventive (instructional) | agent charters |

## Access matrix

| Role | Read job | Write | WebSearch/Fetch | wiki.py | Other scripts | Ledger |
|---|---|---|---|---|---|---|
| Director | ✓ | dispatch/ | ✗ | ✗ | xp, assemble, render, validate, audit, danger, hiscores | seal/unseal/record |
| Intake Officer | ✓ | brief.json | ✗ | ✗ | hiscores, xp | read-only |
| Research desks ×5 | ✓ | own research file, rfi files | ✓ | ✓ | (methods: xp) | read-only |
| Fact Verifier | ✓ | facts.json | ✓ | ✓ | xp, validate | read-only |
| Route Strategist | ✓ | plan.json | ✗ | ✗ | xp | read-only |
| Quant | ✓ | calc-review.json | ✗ | ✗ | xp, validate | read-only |
| Risk Officer | ✓ | risk.json | ✗ | ✗ | danger, xp | read-only |
| Red Team | ✓ | redteam.json | ✓ | ✓ | danger, xp | read-only |
| Guide Author | ✓ | prose.json | ✗ | ✗ | — | read-only |
| Experience Designer | ✓ | templates/ | ✗ | ✗ | render, browser check | read-only |
| QA Auditor | ✓ | qa.json | ✓ | ✓ | validate, audit, browser check, danger, xp | read + **sign** |

## Threat model: failure → control that catches it
- *A researcher hallucinates an XP rate* → verifier re-fetch (5); plan must match the fact (6); QA spot-check (19).
- *A researcher misses a new quest* → Patch Sentinel sweep with 2+ channels; red-team stale-fact hunt; QA recency check.
- *The strategist sneaks in an unverified method* → plan cites only VERIFIED facts (6); no web access (1).
- *The risk officer under-rates to fit the cap* → evidence required; scores computed by code; red-team "mitigation optimism" attack; floors and the 30% residual minimum.
- *The author softens a warning or adds a number* → prose gate (8); QA reading pass.
- *Someone edits a file after review* → seal hash mismatch (3, 13); the release is revoked automatically.
- *The Director steers an agent with undisclosed instructions* → dispatch hash mismatch (15).
- *An agent claims it checked a source it never fetched* → provenance vs Sentry (16).
- *A web page contains "ignore previous instructions"* → injection hygiene (20); tool and write scopes limit any damage (1, 2, 17).

## Known limits (stated honestly)
- Sentry identifies agents from the `agent_type` field that Claude Code passes to hooks. The first identified event switches on strict per-role checks. If a future Claude Code stopped sending it, Sentry would fall back to the global rules and log `role: null`.
- The Director seals on behalf of agents, so the `author` field on a seal is the Director's assertion. The audit cross-check is what corroborates it (who wrote the file, according to Sentry).
- Hooks and agents load when a Claude Code session **starts in this folder**. Start the session from the project root, or the Sentry controls are not active.
- Model-level honesty can't be enforced mechanically. That is why the company layers independent re-checks rather than relying on any single agent.
