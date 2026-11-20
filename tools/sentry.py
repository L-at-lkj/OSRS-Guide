#!/usr/bin/env python3
"""Sentry: the company's independent observer and gatekeeper (a Claude Code hook).

Registered in .claude/settings.json for PreToolUse, PostToolUse,
SubagentStart, SubagentStop, UserPromptSubmit and Stop. For every event it
appends one record to audit/actions.jsonl, a hash-chained, append-only log
that no agent can write to (the guard below blocks Write/Edit on audit/ and
on every ledger, and Bash redirection is not allowed).

On PreToolUse it also *enforces* the minimal-trust policy and records the
decision (allow / block + reason) in the same entry:
  * file writes only inside the project's jobs/, templates/ and cache/ dirs
  * never to audit/, a ledger.jsonl, or any currently sealed handoff file
  * per-role write scopes, when Claude Code tells us which agent is calling
  * Bash limited to an allowlist (python3 tools/*, read-only inspection),
    no chaining, substitution or redirection
  * ledger seal/unseal/record/sign only by the role entitled to them
  * web tools only for research, verification, red-team and QA roles

Set OSRS_GOVERNANCE_MODE=1 in the environment when *you* (the human owner)
want to edit the company itself; it lifts the guard (except audit/ and
ledgers), and every action is still logged with governance=true.

Exit code 2 blocks the tool call and shows the reason to the agent.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("OSRS_COMPANY_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR")
            or Path(__file__).resolve().parent.parent).resolve()
AUDIT_DIR = ROOT / "audit"
AUDIT_LOG = AUDIT_DIR / "actions.jsonl"
LOCK = AUDIT_DIR / ".lock"
IDENTITY_MARK = AUDIT_DIR / ".identity_supported"
ACTIVE = ROOT / "jobs" / ".active"
GOVERNANCE = os.environ.get("OSRS_GOVERNANCE_MODE") == "1"
# observe: log every decision ("would_block") without blocking. Used only when the company runs inside a
# session that did not start in the project folder (agents/hooks not natively registered).
OBSERVE_ONLY = os.environ.get("OSRS_SENTRY_MODE") == "observe"

RESEARCHERS = {"patch-sentinel", "methods-analyst", "quest-archivist", "threat-analyst", "logistics-analyst"}
WEB_ROLES = RESEARCHERS | {"fact-verifier", "red-team", "qa-auditor", "intake-officer"}
RFI = "research/claims-rfi-"
WRITE_SCOPE = {
    "intake-officer": ["brief.json"],
    "patch-sentinel": ["research/updates.json", RFI],
    "methods-analyst": ["research/claims-methods.json", RFI],
    "quest-archivist": ["research/claims-quests.json", RFI],
    "threat-analyst": ["research/claims-threats.json", RFI],
    "logistics-analyst": ["research/claims-logistics.json", RFI],
    "fact-verifier": ["facts.json", "facts-parts/"],
    "route-strategist": ["plan.json"],
    "quant": ["calc-review.json"],
    "risk-officer": ["risk.json"],
    "red-team": ["redteam.json"],
    "guide-author": ["prose.json"],
    "qa-auditor": ["qa.json"],
    "experience-designer": [],  # templates/ only, handled separately
    "director": ["dispatch/"],
}
# Which tools/* scripts each role may run (None = main session / director).
TOOL_SCOPE = {
    "intake-officer": {"hiscores.py", "xp.py"},
    "patch-sentinel": {"wiki.py"}, "methods-analyst": {"wiki.py", "xp.py"},
    "quest-archivist": {"wiki.py"}, "threat-analyst": {"wiki.py"}, "logistics-analyst": {"wiki.py"},
    "fact-verifier": {"wiki.py", "xp.py", "validate.py"},
    "route-strategist": {"xp.py"}, "quant": {"xp.py", "validate.py"},
    "risk-officer": {"danger.py", "xp.py"}, "red-team": {"wiki.py", "danger.py", "xp.py"},
    "guide-author": set(), "experience-designer": {"render.py", "browser_check.mjs"},
    "qa-auditor": {"validate.py", "ledger.py", "wiki.py", "browser_check.mjs", "audit.py", "danger.py", "xp.py"},
    "director": {"ledger.py", "xp.py", "assemble.py", "render.py", "validate.py", "audit.py",
                 "danger.py", "hiscores.py", "browser_check.mjs", "merge_facts.py", "companion.py"},
}
READ_ONLY_CMDS = {"ls", "cat", "head", "tail", "wc", "grep", "rg", "diff", "sha256sum", "jq", "pwd", "date", "stat", "file", "tree"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def active_job() -> str | None:
    try:
        return ACTIVE.read_text().strip() or None
    except OSError:
        return None


def identity(payload: dict) -> str | None:
    """Role of the caller: agent_type for subagents, 'director' for the main session."""
    agent = payload.get("agent_type") or payload.get("subagent_type")
    if agent:
        return agent
    if IDENTITY_MARK.exists():  # this Claude Code reports agent identity, so absence => main session
        return "director"
    return None  # unknown: per-role rules cannot be applied


def summarise_input(tool: str, ti: dict) -> dict:
    ti = ti or {}
    out = {}
    for k in ("file_path", "path", "command", "url", "query", "pattern", "subagent_type", "description", "skill", "prompt"):
        if k in ti:
            v = str(ti[k])
            out[k] = v if len(v) <= 1500 else v[:1500] + f"... [{len(v)} chars]"
    if "prompt" in ti:  # Agent dispatches: lets audit.py prove the prompt matches the sealed dispatch file
        out["prompt_sha256"] = sha(str(ti["prompt"]))
    for k in ("content", "new_string", "old_string"):
        if k in ti:
            out[k + "_sha256"] = sha(str(ti[k]))
            out[k + "_chars"] = len(str(ti[k]))
    return out


# ------------------------------------------------------------------ guard
def sealed_paths(job_path: Path) -> set[str]:
    state: dict[str, bool] = {}
    led = job_path / "ledger.jsonl"
    if not led.exists():
        return set()
    for line in led.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("event") == "seal":
            state[e["path"]] = True
        elif e.get("event") == "unseal":
            state[e["path"]] = False
    return {p for p, s in state.items() if s}


def check_write(path_str: str, role: str | None) -> str | None:
    p = Path(path_str)
    if not p.is_absolute():
        p = ROOT / p
    p = p.resolve()
    if p == AUDIT_DIR or AUDIT_DIR in p.parents:
        return "audit/ is append-only and written by the Sentry hook alone"
    if p.name == "ledger.jsonl":
        return "ledgers are written by tools/ledger.py alone"
    if GOVERNANCE:
        return None
    try:
        rel = p.relative_to(ROOT).as_posix()
    except ValueError:
        return f"writes outside the project are not allowed ({p})"
    if rel.startswith("templates/"):
        if role not in (None, "experience-designer"):
            return f"only the experience-designer edits templates (caller: {role})"
        return None
    if rel.startswith("cache/"):
        return None
    if not rel.startswith("jobs/"):
        return (f"{rel} is company policy/tooling; it can only change in governance mode "
                f"(the owner starts Claude with OSRS_GOVERNANCE_MODE=1)")
    parts = rel.split("/", 2)
    if len(parts) < 3:
        if rel == "jobs/.active" and role in (None, "director"):
            return None
        return f"unexpected path {rel}"
    job, inner = parts[1], parts[2]
    if inner in sealed_paths(ROOT / "jobs" / job):
        return (f"{inner} is SEALED in job {job}. Ask the director to unseal it with a logged reason "
                f"(python3 tools/ledger.py unseal ...) before revising it")
    if role is not None:
        scope = WRITE_SCOPE.get(role)
        if scope is None:
            return f"unknown role {role} may not write job files"
        if not any(inner == s or (s.endswith(("/", "-")) and inner.startswith(s)) for s in scope):
            return f"{role} may only write {scope} in a job (tried {inner})"
    return None


BAD_SHELL = re.compile(r"(;|&&|\|\||`|\$\(|>|<\(|\bsudo\b|\brm\b|\bcurl\b|\bwget\b|\bgit\s+push\b)")


def check_bash(cmd: str, role: str | None) -> str | None:
    if GOVERNANCE:
        return None
    c = cmd.strip()
    m = re.match(r"^cd\s+(\S+)\s*&&\s*(.+)$", c, re.S)
    if m:  # allow a single leading cd into the project
        target = Path(m.group(1).strip("'\"")).expanduser()
        target = (target if target.is_absolute() else ROOT / target).resolve()
        if target != ROOT and ROOT not in target.parents:
            return "cd outside the project is not allowed"
        c = m.group(2).strip()
    if BAD_SHELL.search(c.replace("2>&1", "").replace("2>/dev/null", "")):
        return ("shell chaining, substitution, redirection, rm/curl/wget/sudo and git push are not allowed; "
                "run one python3 tools/<script>.py command (scripts write their own outputs)")
    for seg in c.split("|"):
        try:
            words = shlex.split(seg)
        except ValueError:
            return "could not parse command"
        if not words:
            return "empty pipeline segment"
        head = words[0]
        if head in ("python3", "python", "node"):
            args = [w for w in words[1:] if w not in ("-I", "-u", "-B")]
            if not args or not re.match(r"^(\./)?tools/[a-z_]+\.(py|mjs)$", args[0]):
                return "interpreters may only run scripts in tools/"
            script = args[0].split("/")[-1]
            read_only_ledger = script == "ledger.py" and len(args) > 1 and args[1] in ("verify", "status", "released")
            allowed = TOOL_SCOPE.get(role or "director") if role is not None else None
            if allowed is not None and script not in allowed and not read_only_ledger:
                return f"{role} may not run tools/{script} (allowed: {sorted(allowed)})"
            if script == "ledger.py" and len(args) > 1:
                sub = args[1]
                if sub in ("seal", "unseal", "init", "record") and role not in (None, "director"):
                    return f"only the director runs ledger.py {sub}"
                if sub == "sign" and role not in (None, "qa-auditor", "director"):
                    return "only the qa-auditor signs releases"
                if "--author" in args:
                    author = args[args.index("--author") + 1] if args.index("--author") + 1 < len(args) else ""
                    if role == "qa-auditor" and author != "qa-auditor":
                        return "qa-auditor can only act as itself in the ledger"
        elif head == "mkdir":
            if not all(w.startswith(("jobs/", "-p")) for w in words[1:]):
                return "mkdir only under jobs/"
        elif head not in READ_ONLY_CMDS:
            return f"command '{head}' is not on the allowlist"
    return None


def check_web(tool: str, role: str | None) -> str | None:
    if GOVERNANCE or role is None:
        return None
    if role not in WEB_ROLES:
        return f"{role} has no web access: request facts through the director (RFI) instead"
    return None


def guard(payload: dict, role: str | None) -> str | None:
    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input") or {}
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return check_write(ti.get("file_path") or ti.get("notebook_path") or "", role)
    if tool == "Bash":
        return check_bash(ti.get("command", ""), role)
    if tool in ("WebFetch", "WebSearch"):
        return check_web(tool, role)
    return None


# ------------------------------------------------------------------ audit log
def append_audit(entry: dict) -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "a+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        prev, seq = None, 0
        if AUDIT_LOG.exists():
            with open(AUDIT_LOG, "rb") as fh:
                try:
                    fh.seek(-65536, os.SEEK_END)
                except OSError:
                    fh.seek(0)
                lines = [ln for ln in fh.read().splitlines() if ln.strip()]
            if lines:
                last = json.loads(lines[-1])
                prev, seq = last["entry_hash"], last["seq"] + 1
        entry = {"seq": seq, **entry, "prev": prev}
        entry["entry_hash"] = sha(json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        with open(AUDIT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        fcntl.flock(lk, fcntl.LOCK_UN)


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        payload = {}
    event = payload.get("hook_event_name", sys.argv[1] if len(sys.argv) > 1 else "unknown")
    if payload.get("agent_type") and not IDENTITY_MARK.exists():
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        IDENTITY_MARK.write_text(now())
    role = identity(payload)
    entry = {"ts": now(), "event": event, "job": active_job(), "role": role,
             "agent_id": payload.get("agent_id"), "session_id": payload.get("session_id"),
             "governance": GOVERNANCE}
    block = None
    if event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
        tool = payload.get("tool_name")
        entry.update(tool=tool, tool_use_id=payload.get("tool_use_id"),
                     input=summarise_input(tool, payload.get("tool_input")),
                     input_sha256=sha(json.dumps(payload.get("tool_input"), sort_keys=True, default=str)))
        if event == "PreToolUse":
            block = guard(payload, role)
            entry["decision"] = ("would_block" if OBSERVE_ONLY else "block") if block else "allow"
            if block:
                entry["reason"] = block
            if OBSERVE_ONLY:
                entry["mode"] = "observe"
                block = None
        else:
            resp = payload.get("tool_response")
            text = json.dumps(resp, default=str) if not isinstance(resp, str) else resp
            entry["response_sha256"] = sha(text)
            entry["response_excerpt"] = text[:600]
            entry["is_error"] = event == "PostToolUseFailure" or (isinstance(resp, dict) and bool(resp.get("is_error")))
    elif event in ("SubagentStart", "SubagentStop"):
        entry.update(agent_type=payload.get("agent_type"),
                     agent_transcript_path=payload.get("agent_transcript_path"),
                     transcript_path=payload.get("transcript_path"))
    elif event == "UserPromptSubmit":
        prompt = payload.get("prompt", "")
        entry.update(prompt_excerpt=prompt[:1500], prompt_sha256=sha(prompt),
                     transcript_path=payload.get("transcript_path"))
    else:
        entry["transcript_path"] = payload.get("transcript_path")
    try:
        append_audit(entry)
    except Exception as exc:  # never let logging failure silently pass: block tool use instead
        if event == "PreToolUse":
            print(f"Sentry could not write the audit log ({exc}); refusing unaudited action.", file=sys.stderr)
            sys.exit(2)
    if block:
        print(f"BLOCKED by company policy (minimal trust): {block}", file=sys.stderr)
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
