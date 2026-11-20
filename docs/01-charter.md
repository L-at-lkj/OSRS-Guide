# 01: Company charter

## Mission
Produce the most accurate and current **interactive HTML guides for Old School RuneScape**, built for one-life play on **Hardcore Worlds**. Every recommendation carries an honest, evidence-backed **Danger Score**. Every number can be traced to a source, and every action by every agent can be audited.

## Quality bar ("top level")
A guide ships only when all of these hold:
1. **Complete.** Every level in the requested range has a method. Every quest released in the last 12 months that touches the subject has been evaluated: used, or rejected with a reason.
2. **Correct.** Every number traces to a fact that an independent verifier confirmed from its own fetch of a revision-pinned source. The arithmetic comes from deterministic code, never from a language model.
3. **Current.** Updates were swept no more than 2 days before release. Content under 30 days old carries a caveat.
4. **Safe.** Every step has raw and residual Danger Scores, mitigations, stop conditions, a bail-out plan and a Hardcore Worlds death classification. A `safest` route always exists. Nothing above the owner's cap appears without the owner's recorded acceptance.
5. **Adversarially tested.** A red team tried to get the player killed following the guide literally, and every critical or high finding is resolved.
6. **Auditable.** Chain of custody (ledger), independent observation (Sentry), and self-reported provenance all exist and agree.
7. **Usable.** Interactive, mobile-friendly, light and dark themes, progress tracking, and danger visible at all times.

## Principles
- **Minimal trust.** No agent's output is accepted without an independent check, and that includes the Director. See `03-trust-model.md`.
- **Least privilege.** Each role has only the tools and write scope its job needs.
- **Separation of duties.** Whoever researches a fact doesn't verify it; whoever plans a route doesn't score its danger; whoever writes content doesn't release it.
- **Determinism where possible.** Arithmetic, danger scoring, assembly and rendering are code, so the same inputs always give the same outputs.
- **Safety over speed.** When uncertain, rate danger higher and say why.
- **The owner decides.** Risk acceptance and trade-offs belong to the human who plays the account.

## Owner defaults (from intake, 19 Nov 2026)
- Mode: Hardcore Worlds, **standard** character (trading and the Hardcore Worlds GE).
- Risk appetite: **standard (cap 44)**. A `safest` route is still always produced.
- Runs in: this Claude Code cloud environment (OSRS wiki, hiscores and WikiSync hosts allowed).
