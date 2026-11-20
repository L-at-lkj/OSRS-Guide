#!/usr/bin/env python3
"""Chain-of-custody ledger for a guide job.

Every handoff artifact is *sealed*: its SHA-256 is written to an append-only,
hash-chained ledger (jobs/<id>/ledger.jsonl) together with the role that
produced it. Downstream agents only trust a file whose current hash matches
its latest seal. Editing a sealed file needs an explicit, logged `unseal`.
Sealed files are also write-protected by the guard hook (tools/guard.py).

Commands
  init    <job> --request TEXT          create the job folder and ledger
  seal    <job> <relpath> --author ROLE [--note TEXT]
  unseal  <job> <relpath> --author ROLE --reason TEXT
  sign    <job> --role qa|user --author ROLE --subject RELPATH --decision approve|reject [--note]
  record  <job> --event dispatch|return|decision|veto|lift_veto|accept_risk|rfi|note
                --author ROLE --note TEXT [--ref ID]   (dispatch/return/decision: director only)
  activate <job>                        make <job> the job Sentry tags actions with
  verify  <job>                         check chain + every sealed file (exit 1 on any problem)
  status  <job>                         human summary
  released <job>                        exit 0 only if content.json carries a valid QA approval
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import canonical_json, die, job_dir, now_iso, sha256_bytes, sha256_file  # noqa: E402

ROLES = {
    "director", "intake-officer", "patch-sentinel", "methods-analyst", "quest-archivist",
    "threat-analyst", "logistics-analyst", "fact-verifier", "route-strategist", "quant",
    "risk-officer", "red-team", "guide-author", "experience-designer", "qa-auditor",
    "system", "user",
}

RESEARCHERS = {"patch-sentinel", "methods-analyst", "quest-archivist", "threat-analyst", "logistics-analyst"}

# Separation of duties: which role may seal which artifact.
SEAL_RIGHTS: list[tuple[str, set[str]]] = [
    ("brief.json", {"intake-officer"}),
    ("research/updates.json", {"patch-sentinel"}),
    ("research/claims-methods.json", {"methods-analyst"}),
    ("research/claims-quests.json", {"quest-archivist"}),
    ("research/claims-threats.json", {"threat-analyst"}),
    ("research/claims-logistics.json", {"logistics-analyst"}),
    ("research/claims-rfi-", RESEARCHERS),          # prefix match
    ("facts-parts/", {"fact-verifier"}),           # parallel verifier instances, one per desk
    ("facts.json", {"fact-verifier", "system"}),    # system = tools/merge_facts.py
    ("plan.json", {"route-strategist"}),
    ("calc.json", {"system"}),                      # produced by tools/xp.py only
    ("calc-review.json", {"quant"}),
    ("risk.json", {"risk-officer"}),
    ("anchor-ratings.json", {"risk-officer"}),      # calibration jobs
    ("redteam.json", {"red-team"}),
    ("prose.json", {"guide-author"}),
    ("content.json", {"system"}),                   # produced by tools/assemble.py only
    ("guide.html", {"system"}),                     # produced by tools/render.py only
    ("qa.json", {"qa-auditor"}),
    ("dispatch/", {"director"}),                    # verbatim prompt given to each agent
    ("audit.json", {"system"}),                     # produced by tools/audit.py only
    ("audit.html", {"system"}),
]

# Roles that author guide content; none of them may give the QA release signature.
CONTENT_AUTHORS = RESEARCHERS | {"fact-verifier", "route-strategist", "quant", "risk-officer",
                                 "red-team", "guide-author", "experience-designer", "director"}


def allowed_sealers(relpath: str) -> set[str] | None:
    for pattern, roles in SEAL_RIGHTS:
        if relpath == pattern or (pattern.endswith(("-", "/")) and relpath.startswith(pattern)):
            return roles
    return None


def ledger_path(job: str) -> Path:
    return job_dir(job) / "ledger.jsonl"


def read_entries(job: str) -> list[dict]:
    p = ledger_path(job)
    if not p.exists():
        die(f"job {job!r} has no ledger; run: python3 tools/ledger.py init {job} --request ...")
    entries = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def _entry_hash(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "entry_hash"}
    return sha256_bytes(canonical_json(body).encode())


def append(job: str, entry: dict) -> dict:
    entries = read_entries(job) if ledger_path(job).exists() else []
    entry = {"seq": len(entries), "ts": now_iso(), **entry,
             "prev": entries[-1]["entry_hash"] if entries else None}
    entry["entry_hash"] = _entry_hash(entry)
    with open(ledger_path(job), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def seal_state(entries: list[dict]) -> dict[str, dict]:
    """Map relpath -> {'sealed': bool, 'sha256': str|None, 'author': str, 'version': int}."""
    state: dict[str, dict] = {}
    for e in entries:
        if e["event"] == "seal":
            prev = state.get(e["path"], {"version": 0})
            state[e["path"]] = {"sealed": True, "sha256": e["sha256"], "author": e["author"],
                                "version": prev["version"] + 1}
        elif e["event"] == "unseal":
            s = state.setdefault(e["path"], {"version": 0, "sha256": None, "author": e["author"]})
            s["sealed"] = False
    return state


def cmd_init(a):
    d = job_dir(a.job)
    if (d / "ledger.jsonl").exists():
        die(f"job {a.job} already exists")
    for sub in ("research", "cache"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    e = append(a.job, {"event": "init", "author": "director", "note": a.request})
    (d.parent / ".active").write_text(a.job)  # Sentry tags every audited action with the active job
    print(json.dumps({"job": a.job, "dir": str(d), "entry": e["seq"], "active": True}))


def cmd_activate(a):
    read_entries(a.job)
    (job_dir(a.job).parent / ".active").write_text(a.job)
    print(json.dumps({"active": a.job}))


def cmd_seal(a):
    if a.author not in ROLES:
        die(f"unknown role {a.author}")
    allowed = allowed_sealers(a.path)
    if allowed is None:
        die(f"{a.path} is not a recognised handoff artifact (see SEAL_RIGHTS)")
    if a.author not in allowed:
        die(f"separation of duties: {a.author} may not seal {a.path} (allowed: {sorted(allowed)})")
    f = job_dir(a.job) / a.path
    if not f.exists():
        die(f"{f} does not exist")
    state = seal_state(read_entries(a.job)).get(a.path)
    if state and state["sealed"]:
        die(f"{a.path} is already sealed (v{state['version']}); unseal it with a reason first")
    e = append(a.job, {"event": "seal", "path": a.path, "sha256": sha256_file(f),
                       "author": a.author, "note": a.note or ""})
    print(json.dumps({"sealed": a.path, "sha256": e["sha256"], "seq": e["seq"]}))


def cmd_unseal(a):
    state = seal_state(read_entries(a.job)).get(a.path)
    if not state or not state["sealed"]:
        die(f"{a.path} is not sealed")
    if not a.reason or len(a.reason) < 10:
        die("an unseal needs a real reason (>=10 chars), e.g. the red-team finding id")
    e = append(a.job, {"event": "unseal", "path": a.path, "author": a.author, "note": a.reason})
    print(json.dumps({"unsealed": a.path, "seq": e["seq"]}))


def cmd_sign(a):
    entries = read_entries(a.job)
    state = seal_state(entries).get(a.subject)
    if not state or not state["sealed"]:
        die(f"cannot sign {a.subject}: it is not sealed")
    f = job_dir(a.job) / a.subject
    if sha256_file(f) != state["sha256"]:
        die(f"cannot sign {a.subject}: file differs from its seal (tampering?)")
    if a.role == "qa":
        if a.author != "qa-auditor":
            die("only qa-auditor gives the QA signature")
        authors = {e["author"] for e in entries if e["event"] == "seal"}
        if a.author in authors & CONTENT_AUTHORS:
            die("separation of duties: the QA signer sealed content in this job")
    e = append(a.job, {"event": "sign", "role": a.role, "path": a.subject, "sha256": state["sha256"],
                       "author": a.author, "decision": a.decision, "note": a.note or ""})
    print(json.dumps({"signed": a.subject, "decision": a.decision, "seq": e["seq"]}))


def cmd_record(a):
    if a.author not in ROLES:
        die(f"unknown role {a.author}")
    if a.event == "veto" and a.author not in {"risk-officer", "qa-auditor", "fact-verifier", "user"}:
        die("only risk-officer, fact-verifier, qa-auditor or the user may veto")
    if a.event == "lift_veto" and a.author not in {"risk-officer", "user"}:
        die("only the risk-officer (own vetoes) or the user may lift a veto")
    if a.event == "accept_risk" and a.author != "user":
        die("only the user can accept a risk")
    if a.event in ("dispatch", "return", "decision") and a.author != "director":
        die(f"{a.event} events are recorded by the director")
    if a.event == "dispatch":
        ref = a.ref or ""
        st = seal_state(read_entries(a.job)).get(ref)
        if not ref.startswith("dispatch/") or not st or not st["sealed"]:
            die("a dispatch must --ref the sealed dispatch/NNN-<agent>.md prompt file")
    e = append(a.job, {"event": a.event, "author": a.author, "note": a.note, "ref": a.ref or ""})
    print(json.dumps({"recorded": a.event, "seq": e["seq"]}))


def verify(job: str) -> list[str]:
    problems = []
    entries = read_entries(job)
    prev = None
    for e in entries:
        if e.get("prev") != prev:
            problems.append(f"ledger chain broken at seq {e.get('seq')}")
        if _entry_hash(e) != e.get("entry_hash"):
            problems.append(f"ledger entry {e.get('seq')} was altered")
        prev = e.get("entry_hash")
    d = job_dir(job)
    state = seal_state(entries)
    for path, s in state.items():
        f = d / path
        if s["sealed"]:
            if not f.exists():
                problems.append(f"sealed file missing: {path}")
            elif sha256_file(f) != s["sha256"]:
                problems.append(f"TAMPER: {path} changed after it was sealed by {s['author']}")
    known = set(state) | {"ledger.jsonl"}
    for f in d.rglob("*"):
        rel = f.relative_to(d).as_posix()
        if f.is_file() and rel not in known and not rel.startswith(("cache/", "transcripts/", "screens/")):
            problems.append(f"unsealed file present (not trusted by anyone): {rel}")
    return problems


def open_vetoes(entries: list[dict]) -> list[dict]:
    vetoes = {e["ref"] or str(e["seq"]): e for e in entries if e["event"] == "veto"}
    for e in entries:
        if e["event"] == "lift_veto" and e["ref"] in vetoes:
            vetoes.pop(e["ref"])
    return list(vetoes.values())


def release_status(job: str) -> dict:
    entries = read_entries(job)
    state = seal_state(entries)
    content = state.get("content.json")
    out = {"released": False, "content_sha256": content["sha256"] if content else None, "reasons": []}
    if not content or not content["sealed"]:
        out["reasons"].append("content.json is not sealed")
        return out
    approvals = [e for e in entries if e["event"] == "sign" and e.get("role") == "qa"
                 and e["path"] == "content.json" and e["sha256"] == content["sha256"]]
    if not approvals or approvals[-1]["decision"] != "approve":
        out["reasons"].append("no QA approval for the current content.json")
    if open_vetoes(entries):
        out["reasons"].append(f"{len(open_vetoes(entries))} open veto(es)")
    problems = verify(job)
    tamper = [p for p in problems if not p.startswith("unsealed file present")]
    if tamper:
        out["reasons"] += tamper
    out["released"] = not out["reasons"]
    if approvals:
        out["approved_at"] = approvals[-1]["ts"]
    return out


def cmd_verify(a):
    problems = verify(a.job)
    for p in problems:
        print(("WARN  " if p.startswith("unsealed") else "FAIL  ") + p)
    hard = [p for p in problems if not p.startswith("unsealed")]
    print("OK: ledger chain and all seals intact" if not hard else f"{len(hard)} integrity failure(s)")
    sys.exit(1 if hard else 0)


def cmd_status(a):
    entries = read_entries(a.job)
    print(f"Job {a.job}: {len(entries)} ledger entries")
    for path, s in sorted(seal_state(entries).items()):
        flag = "SEALED  " if s["sealed"] else "EDITING "
        print(f"  {flag} v{s['version']}  {path:38s} by {s['author']}")
    for v in open_vetoes(entries):
        print(f"  OPEN VETO [{v['ref']}] by {v['author']}: {v['note']}")
    rs = release_status(a.job)
    print("  RELEASE: " + ("APPROVED" if rs["released"] else "not released — " + "; ".join(rs["reasons"])))


def cmd_released(a):
    rs = release_status(a.job)
    print(json.dumps(rs, indent=2))
    sys.exit(0 if rs["released"] else 1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("init"); s.add_argument("job"); s.add_argument("--request", required=True); s.set_defaults(f=cmd_init)
    s = sp.add_parser("seal"); s.add_argument("job"); s.add_argument("path"); s.add_argument("--author", required=True); s.add_argument("--note"); s.set_defaults(f=cmd_seal)
    s = sp.add_parser("unseal"); s.add_argument("job"); s.add_argument("path"); s.add_argument("--author", required=True); s.add_argument("--reason", required=True); s.set_defaults(f=cmd_unseal)
    s = sp.add_parser("sign"); s.add_argument("job"); s.add_argument("--role", choices=["qa", "user"], required=True); s.add_argument("--author", required=True); s.add_argument("--subject", required=True); s.add_argument("--decision", choices=["approve", "reject"], required=True); s.add_argument("--note"); s.set_defaults(f=cmd_sign)
    s = sp.add_parser("record"); s.add_argument("job"); s.add_argument("--event", choices=["dispatch", "return", "decision", "veto", "lift_veto", "accept_risk", "rfi", "note"], required=True); s.add_argument("--author", required=True); s.add_argument("--note", required=True); s.add_argument("--ref"); s.set_defaults(f=cmd_record)
    for name, fn in (("activate", cmd_activate), ("verify", cmd_verify), ("status", cmd_status), ("released", cmd_released)):
        s = sp.add_parser(name); s.add_argument("job"); s.set_defaults(f=fn)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
