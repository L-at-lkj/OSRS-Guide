# 09: How to audit anything the company did

Three independent records exist. No agent can rewrite any of them without detection.

| Record | Written by | Contains | Tamper evidence |
|---|---|---|---|
| `audit/actions.jsonl` | **Sentry hook only** (agents are blocked from writing it) | Every tool call by every agent: who (role, agent id), what (tool, command, file, URL, query, prompt hash), whether it was **allowed or blocked and why**, the result (hash and excerpt), agent start/stop, transcript paths, and your own prompts | Hash chain (`prev` + `entry_hash`). `python3 tools/audit.py verify` |
| `jobs/<job>/ledger.jsonl` | `tools/ledger.py` only | Job opened; every dispatch (with the sealed prompt file); every seal and unseal (artifact hash, author, reason); vetoes; your risk acceptances (verbatim); QA signature | Hash chain plus a seal hash per artifact. `python3 tools/ledger.py verify <job>` |
| `provenance` in every artifact | Each agent, about itself | Inputs (path and hash), actions (searches, fetches with exact URL or revid), decisions with reasons and alternatives, limitations | Cross-checked against the two records above |

## Questions → commands
| You want to know… | Run |
|---|---|
| Is everything intact? | `python3 tools/audit.py verify` · `python3 tools/ledger.py verify <job>` |
| Status of a job, open vetoes, release state | `python3 tools/ledger.py status <job>` |
| Everything that happened, in order | `python3 tools/audit.py timeline <job>` |
| What one agent did | `python3 tools/audit.py timeline <job> --role threat-analyst` |
| Activity per agent (calls, blocks, errors, tools) | `python3 tools/audit.py agents <job>` |
| Did agents do what they claim? Did the Director send undisclosed instructions? | `python3 tools/audit.py crosscheck <job>` |
| Exactly what the Director told an agent | `jobs/<job>/dispatch/NNN-<agent>.md` |
| Why an agent made a decision | the `provenance.decisions` of its artifact (also the Audit tab in the guide) |
| The full conversation of an agent | `jobs/<job>/transcripts/` (archived by `audit.py export`) |
| A browsable report | `jobs/<job>/audit.html`: filter by agent, full-text search, cross-check results, provenance |
| Where a number in the guide came from | the guide's fact chip → Sources tab → revision-pinned link. Or `content.json` → fact → claim → research file → provenance |

## What the cross-check flags
- **FAIL**: an agent was dispatched with a prompt that matches no sealed dispatch file; a sealed artifact changed; a ledger or audit entry was altered; an artifact has no provenance.
- **WARN**: an agent claims a fetch Sentry never saw; a ledger seal was not observed through the audited path; blocked actions (attempted policy violations, listed with reasons); no Sentry data for the job (hooks inactive).
