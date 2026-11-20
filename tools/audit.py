#!/usr/bin/env python3
"""Audit office: makes every action by every agent inspectable and checkable.

Three independent records exist for a job:
  1. audit/actions.jsonl   - what the Sentry hook OBSERVED (every tool call,
                              allowed or blocked, every agent start/stop)
  2. jobs/<id>/ledger.jsonl - what was SEALED, dispatched, signed, vetoed
  3. provenance blocks      - what each agent SAYS it did and why
This tool verifies each record and cross-checks them against one another.

Commands
  verify                       hash-chain integrity of audit/actions.jsonl
  timeline <job> [--role R]    merged, chronological view of a job
  agents <job>                 per-agent activity table
  crosscheck <job>             compare claims vs observations (exit 1 on FAIL)
  export <job>                 write jobs/<id>/audit.json + audit.html and
                               archive agent transcripts into jobs/<id>/transcripts/
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, job_dir, load_json, now_iso, save_json, sha256_file  # noqa: E402
import ledger  # noqa: E402

AUDIT_LOG = ROOT / "audit" / "actions.jsonl"
ARTIFACTS = ["brief.json", "research/updates.json", "research/claims-methods.json", "research/claims-quests.json",
             "research/claims-threats.json", "research/claims-logistics.json", "facts.json", "plan.json",
             "calc-review.json", "risk.json", "redteam.json", "prose.json", "qa.json"]


def load_actions(job: str | None = None) -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    out = []
    for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines():
        if line.strip():
            e = json.loads(line)
            if job is None or e.get("job") == job:
                out.append(e)
    return out


def verify_chain() -> list[str]:
    problems, prev = [], None
    for e in load_actions():
        body = {k: v for k, v in e.items() if k != "entry_hash"}
        h = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                           .encode("utf-8", "replace")).hexdigest()
        if h != e.get("entry_hash"):
            problems.append(f"audit entry {e.get('seq')} altered")
        if e.get("prev") != prev:
            problems.append(f"audit chain broken before entry {e.get('seq')}")
        prev = e.get("entry_hash")
    return problems


def agent_table(job: str) -> dict:
    acts = load_actions(job)
    t: dict[str, dict] = {}
    for e in acts:
        role = e.get("role") or e.get("agent_type") or "unidentified"
        row = t.setdefault(role, {"tool_calls": 0, "blocked": 0, "errors": 0, "tools": {}, "web_targets": [],
                                  "starts": 0, "first": e["ts"], "last": e["ts"], "blocked_reasons": []})
        row["last"] = e["ts"]
        if e["event"] == "PreToolUse":
            row["tool_calls"] += 1
            row["tools"][e.get("tool")] = row["tools"].get(e.get("tool"), 0) + 1
            if e.get("decision") in ("block", "would_block"):
                row["blocked"] += 1
                row["blocked_reasons"].append(e.get("reason", ""))
            inp = e.get("input", {})
            tgt = inp.get("url") or inp.get("query") or (inp.get("command") if "wiki.py" in inp.get("command", "") else None)
            if tgt:
                row["web_targets"].append(tgt[:200])
        elif e["event"] in ("PostToolUse", "PostToolUseFailure") and e.get("is_error"):
            row["errors"] += 1
        elif e["event"] == "SubagentStart":
            row["starts"] += 1
    return t


def provenance_of(job: str) -> dict:
    d = job_dir(job)
    out = {}
    for rel in ARTIFACTS:
        p = d / rel
        if p.exists():
            try:
                out[rel] = load_json(p).get("provenance")
            except ValueError:
                out[rel] = None
    return out


def crosscheck(job: str) -> list[tuple[str, str]]:
    """Returns [(level, message)] with level FAIL/WARN/OK."""
    res = []
    for p in verify_chain():
        res.append(("FAIL", p))
    for p in ledger.verify(job):
        res.append(("WARN" if p.startswith("unsealed") else "FAIL", "ledger: " + p))
    acts = load_actions(job)
    entries = ledger.read_entries(job)
    d = job_dir(job)
    # 1. dispatch prompts sent == dispatch prompts on file
    sealed_dispatch = {}
    for e in entries:
        if e["event"] == "seal" and e["path"].startswith("dispatch/"):
            sealed_dispatch[e["sha256"]] = e["path"]
    sent = [e for e in acts if e["event"] == "PreToolUse" and e.get("tool") in ("Agent", "Task")
            and e.get("decision") in ("allow", "would_block")]
    sent_hashes = set()
    for e in sent:
        h = e.get("input", {}).get("prompt_sha256")
        sent_hashes.add(h)
        if h not in sealed_dispatch:
            res.append(("FAIL", f"agent dispatched at {e['ts']} ({e['input'].get('subagent_type')}) with a prompt "
                                f"that matches no sealed dispatch/ file (undocumented instructions)"))
    for h, path in sealed_dispatch.items():
        if acts and h not in sent_hashes:
            res.append(("WARN", f"{path} sealed but no matching Agent call observed"))
    if sent and not [r for r in res if r[1].startswith("agent dispatched")]:
        res.append(("OK", f"all {len(sent)} agent dispatches match sealed prompts"))
    # 2. every ledger seal was observed being executed through the audited path
    seal_cmds = [e.get("input", {}).get("command", "") for e in acts
                 if e["event"] == "PreToolUse" and e.get("tool") == "Bash" and e.get("decision") in ("allow", "would_block")]
    if acts:
        for e in entries:
            if e["event"] in ("seal", "unseal", "sign"):
                needle = e["path"]
                if not any("ledger.py" in c and e["event"] in c and needle in c for c in seal_cmds):
                    res.append(("WARN", f"ledger {e['event']} of {needle} (seq {e['seq']}) not seen in the audit log "
                                        f"(run outside an audited session?)"))
    # 3. self-reported fetches vs observed fetches
    observed = " ".join(json.dumps(e.get("input", {})) for e in acts if e["event"] == "PreToolUse")
    for rel, prov in provenance_of(job).items():
        if not prov:
            res.append(("FAIL" if rel != "qa.json" else "WARN", f"{rel}: no provenance block"))
            continue
        for act in prov.get("actions", []):
            if act["kind"] in ("fetch", "search") and act.get("target") and acts:
                tgt = act["target"]
                key = tgt.split("oldid=")[-1] if "oldid=" in tgt else tgt[:60]
                if key not in observed:
                    res.append(("WARN", f"{rel}: claims {act['kind']} of {tgt[:80]!r} but Sentry never observed it"))
    # 4. attempted policy violations
    for role, row in agent_table(job).items():
        if row["blocked"]:
            res.append(("WARN", f"{role}: {row['blocked']} blocked action(s): " + " | ".join(row["blocked_reasons"][:3])))
    if not acts:
        res.append(("WARN", "no Sentry observations for this job (hooks inactive, or job not activated)"))
    return res


def timeline(job: str, role: str | None = None) -> list[dict]:
    items = []
    for e in ledger.read_entries(job):
        items.append({"ts": e["ts"], "source": "ledger", "who": e.get("author"), "what": e["event"],
                      "detail": (e.get("path") or "") + (" " + e.get("note", "") if e.get("note") else "")})
    for e in load_actions(job):
        who = e.get("role") or e.get("agent_type") or "unidentified"
        if e["event"] == "PreToolUse":
            inp = e.get("input", {})
            det = inp.get("command") or inp.get("file_path") or inp.get("url") or inp.get("query") or inp.get("subagent_type") or ""
            what = f"{e.get('tool')} [{e.get('decision')}]"
            if e.get("decision") in ("block", "would_block"):
                det += f"  <- {e.get('decision').upper()}: {e.get('reason')}"
        elif e["event"] in ("PostToolUse", "PostToolUseFailure"):
            if not e.get("is_error"):
                continue
            what, det = f"{e.get('tool')} error", e.get("response_excerpt", "")[:160]
        else:
            what, det = e["event"], e.get("agent_type") or e.get("prompt_excerpt", "")[:160]
        items.append({"ts": e["ts"], "source": "sentry", "who": who, "what": what, "detail": str(det)[:400]})
    items.sort(key=lambda x: x["ts"])
    return [i for i in items if not role or i["who"] == role]


def summary(job: str) -> dict:
    entries = ledger.read_entries(job)
    return {
        "generated_at": now_iso(),
        "ledger": [{k: e.get(k) for k in ("seq", "ts", "event", "path", "author", "sha256", "decision", "note", "ref")}
                   for e in entries],
        "agents": agent_table(job),
        "provenance": provenance_of(job),
        "crosscheck": [{"level": l, "message": m} for l, m in crosscheck(job)],
        "release": ledger.release_status(job),
        "audit_log_head": (load_actions() or [{}])[-1].get("entry_hash"),
        "timeline": timeline(job),
    }


AUDIT_HTML = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audit trail: __JOB__</title><style>
:root{--bg:#f6f1e4;--fg:#2b2418;--muted:#6b5f49;--line:#d8ccb0;--card:#fffaf0;--bad:#a1271b;--warn:#8a5a00;--ok:#2e6b30}
@media (prefers-color-scheme:dark){:root{--bg:#16130f;--fg:#ece3cf;--muted:#a99b80;--line:#3a3226;--card:#1f1a14;--bad:#ff8a7a;--warn:#e8b860;--ok:#8fd18f}}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif}main{max-width:1200px;margin:0 auto;padding:16px}
h1{font-family:Georgia,serif;margin:.2em 0}table{width:100%;border-collapse:collapse;background:var(--card)}td,th{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{font-size:12px;text-transform:uppercase;color:var(--muted)}.FAIL{color:var(--bad);font-weight:700}.WARN{color:var(--warn)}.OK{color:var(--ok)}
code{font-size:12px;word-break:break-all}.wrap{overflow-x:auto}select,input{font:inherit;padding:4px 8px;margin:4px 8px 12px 0}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 12px;margin:8px 0}</style></head><body><main>
<h1>Audit trail: __JOB__</h1><p>Generated __TS__. Ledger entries and Sentry observations, merged. Every row is backed by a hash-chained record.</p>
<h2>Cross-check</h2><div id="cc"></div><h2>Agents</h2><div class="wrap" id="agents"></div>
<h2>Timeline</h2><label>Who <select id="who"><option value="">everyone</option></select></label><label>Search <input id="q"></label>
<div class="wrap"><table id="tl"><thead><tr><th>Time (UTC)</th><th>Source</th><th>Who</th><th>What</th><th>Detail</th></tr></thead><tbody></tbody></table></div>
<h2>Provenance (what each agent reports)</h2><div id="prov"></div></main>
<script type="application/json" id="audit-data">__DATA__</script><script>
const A=JSON.parse(document.getElementById('audit-data').textContent);const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
document.getElementById('cc').innerHTML='<table>'+A.crosscheck.map(c=>`<tr><td class="${c.level}">${c.level}</td><td>${esc(c.message)}</td></tr>`).join('')+'</table>';
document.getElementById('agents').innerHTML='<table><tr><th>Role</th><th>Tool calls</th><th>Blocked</th><th>Errors</th><th>Tools</th><th>Active</th></tr>'+Object.entries(A.agents).map(([r,v])=>`<tr><td>${esc(r)}</td><td>${v.tool_calls}</td><td class="${v.blocked?'WARN':''}">${v.blocked}</td><td>${v.errors}</td><td>${esc(Object.entries(v.tools).map(([t,n])=>t+'×'+n).join(', '))}</td><td>${esc(v.first)} → ${esc(v.last)}</td></tr>`).join('')+'</table>';
const who=document.getElementById('who');[...new Set(A.timeline.map(t=>t.who))].forEach(w=>who.insertAdjacentHTML('beforeend',`<option>${esc(w)}</option>`));
function draw(){const q=document.getElementById('q').value.toLowerCase();document.querySelector('#tl tbody').innerHTML=A.timeline.filter(t=>(!who.value||t.who===who.value)&&(!q||JSON.stringify(t).toLowerCase().includes(q))).map(t=>`<tr><td><code>${esc(t.ts)}</code></td><td>${esc(t.source)}</td><td>${esc(t.who)}</td><td>${esc(t.what)}</td><td><code>${esc(t.detail)}</code></td></tr>`).join('')}
who.onchange=draw;document.getElementById('q').oninput=draw;draw();
document.getElementById('prov').innerHTML=Object.entries(A.provenance).map(([f,p])=>`<details><summary><b>${esc(f)}</b> — ${esc(p?.agent||'no provenance')}</summary>${p?`<p>${esc(p.started_at)} → ${esc(p.finished_at)}</p><h4>Inputs</h4><ul>${p.inputs.map(i=>`<li>${esc(i.path)} <code>${esc(i.sha256.slice(0,16))}…</code></li>`).join('')}</ul><h4>Actions</h4><ol>${p.actions.map(a=>`<li><b>${esc(a.kind)}</b> ${esc(a.detail)} ${a.target?`<code>${esc(a.target)}</code>`:''} ${a.outcome?'→ '+esc(a.outcome):''}</li>`).join('')}</ol><h4>Decisions</h4><ul>${p.decisions.map(x=>`<li><b>${esc(x.decision)}</b>: ${esc(x.reason)}${x.alternatives_considered?.length?' (considered: '+esc(x.alternatives_considered.join('; '))+')':''}</li>`).join('')}</ul><h4>Limitations</h4><ul>${p.limitations.map(l=>`<li>${esc(l)}</li>`).join('')}</ul>`:''}</details>`).join('');
</script></body></html>"""


def export(job: str):
    d = job_dir(job)
    tdir = d / "transcripts"
    archived = []
    for e in load_actions(job):
        for k in ("agent_transcript_path", "transcript_path"):
            src = e.get(k)
            if src and Path(src).exists():
                dst = tdir / (e.get("agent_id") or Path(src).stem) / Path(src).name
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    archived.append({"path": dst.relative_to(d).as_posix(), "sha256": sha256_file(dst)})
    data = summary(job)
    data["transcripts"] = archived
    save_json(d / "audit.json", data)
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    (d / "audit.html").write_text(AUDIT_HTML.replace("__JOB__", html.escape(job)).replace("__TS__", data["generated_at"])
                                  .replace("__DATA__", payload), encoding="utf-8")
    print(f"wrote {d / 'audit.json'} and {d / 'audit.html'}; archived {len(archived)} transcript(s)")
    print("seal with: python3 tools/ledger.py seal", job, "audit.json --author system  (and audit.html)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("verify")
    s = sp.add_parser("timeline"); s.add_argument("job"); s.add_argument("--role")
    s = sp.add_parser("agents"); s.add_argument("job")
    s = sp.add_parser("crosscheck"); s.add_argument("job")
    s = sp.add_parser("export"); s.add_argument("job")
    a = p.parse_args()
    if a.cmd == "verify":
        probs = verify_chain()
        print("\n".join(probs) or f"OK: {len(load_actions())} audit entries, chain intact")
        sys.exit(1 if probs else 0)
    if a.cmd == "timeline":
        for t in timeline(a.job, a.role):
            print(f"{t['ts']}  {t['source']:6s} {t['who']:18s} {t['what']:28s} {t['detail'][:140]}")
    elif a.cmd == "agents":
        for role, row in agent_table(a.job).items():
            print(f"{role:20s} calls={row['tool_calls']:4d} blocked={row['blocked']:3d} errors={row['errors']:3d} "
                  f"tools={row['tools']}")
    elif a.cmd == "crosscheck":
        res = crosscheck(a.job)
        for lvl, m in res:
            print(f"{lvl:5s} {m}")
        sys.exit(1 if any(l == "FAIL" for l, _ in res) else 0)
    else:
        export(a.job)


if __name__ == "__main__":
    main()
