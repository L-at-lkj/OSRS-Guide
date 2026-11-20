#!/usr/bin/env python3
"""Stage gates. A stage passes only when this script says so.

  python3 tools/validate.py <job> <stage>
  stages: brief research facts plan calc risk redteam prose content html release all

Every gate is mechanical: schema conformance, cross-references between
artifacts, separation of duties, recomputed numbers, provenance hashes.
Output lines start with FAIL / WARN / OK; exit code 1 when anything FAILs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, job_dir, load_json, sha256_file, validate_against  # noqa: E402
import danger  # noqa: E402
import ledger  # noqa: E402

GOOD = {"VERIFIED", "VERIFIED_WITH_CAVEAT"}
COMPANY_FILES = ("docs/", "schemas/", ".claude/", "tools/", "templates/", "policy/", "profiles/")
DESK_PREFIX = {"methods": "MTH", "quests": "QST", "threats": "THR", "logistics": "LOG", "updates": "UPD", "rfi": "RFI"}
RESEARCH_FILES = ["research/updates.json", "research/claims-methods.json", "research/claims-quests.json",
                  "research/claims-threats.json", "research/claims-logistics.json"]
TOKEN_RE = re.compile(r"\{\{\s*(step\.(actions|hours|start_level|end_level|xp_gained|start_xp|end_xp)|"
                      r"fact:F-\d{4}|risk\.(min_hitpoints|residual_ds|inherent_ds|tier))\s*\}\}")


class Report:
    def __init__(self):
        self.fails, self.warns, self.oks = [], [], []

    def fail(self, m): self.fails.append(m)
    def warn(self, m): self.warns.append(m)
    def ok(self, m): self.oks.append(m)

    def print(self):
        for m in self.oks:
            print("OK    " + m)
        for m in self.warns:
            print("WARN  " + m)
        for m in self.fails:
            print("FAIL  " + m)
        print(f"== {len(self.fails)} fail, {len(self.warns)} warn")


def _d(job): return job_dir(job)


def _load(job, rel, r: Report, schema=None):
    p = _d(job) / rel
    if not p.exists():
        r.fail(f"{rel} missing")
        return None
    try:
        data = load_json(p)
    except ValueError as exc:
        r.fail(f"{rel} is not valid JSON: {exc}")
        return None
    if schema:
        errs = validate_against(data, schema)
        for e in errs[:25]:
            r.fail(f"{rel} schema: {e}")
        if not errs:
            r.ok(f"{rel} matches schema {schema}")
    return data


def _sealed(job, rel, r: Report, required=True):
    entries = ledger.read_entries(job)
    st = ledger.seal_state(entries).get(rel)
    if not st or not st["sealed"]:
        (r.fail if required else r.warn)(f"{rel} is not sealed in the ledger")
        return None
    if sha256_file(_d(job) / rel) != st["sha256"]:
        r.fail(f"{rel} differs from its seal (tampered or edited without unseal)")
        return None
    return st


def check_provenance(job, rel, data, r: Report, expect_agent=None):
    prov = (data or {}).get("provenance")
    if not prov:
        return
    if expect_agent and prov.get("agent") != expect_agent:
        r.fail(f"{rel}: provenance.agent is {prov.get('agent')!r}, expected {expect_agent!r}")
    entries = ledger.read_entries(job)
    seen = {}
    for e in entries:
        if e["event"] == "seal":
            seen.setdefault(e["path"], set()).add(e["sha256"])
    for inp in prov.get("inputs", []):
        if inp["path"].startswith(COMPANY_FILES):  # governed company reference files: check against current
            cf = ROOT / inp["path"]
            if not cf.exists():
                r.fail(f"{rel}: provenance input {inp['path']} does not exist")
            elif sha256_file(cf) != inp["sha256"]:
                r.warn(f"{rel}: company file {inp['path']} changed since the agent read it")
            continue
        hashes = seen.get(inp["path"])
        if hashes is None:
            r.fail(f"{rel}: provenance input {inp['path']} was never sealed (agent worked from untrusted data)")
        elif inp["sha256"] not in hashes:
            r.fail(f"{rel}: provenance input {inp['path']} hash matches no sealed version")
    if not prov.get("actions"):
        r.fail(f"{rel}: provenance has no actions")


# ------------------------------------------------------------------ stages
def g_brief(job, r):
    b = _load(job, "brief.json", r, "brief")
    if not b:
        return
    _sealed(job, "brief.json", r, required=False)
    check_provenance(job, "brief.json", b, r, "intake-officer")
    gm = b["game_mode"]
    if gm["world_type"] == "hardcore_worlds" and gm["death_ruleset"] != "hardcore_worlds":
        r.fail("brief: Hardcore Worlds accounts must use the hardcore_worlds death ruleset")
    try:
        frm = dt.date.fromisoformat(b["recency_window"]["from"][:10])
        to = dt.date.fromisoformat(b["recency_window"]["to"][:10])
        if (to - frm).days < 360:
            r.fail("brief: recency window must cover at least the last 12 months")
    except ValueError:
        r.fail("brief: recency window dates must be ISO dates")
    if b["profile"]["stats_source"] == "user_stated":
        r.warn("brief: stats are user-stated, not verified against hiscores/WikiSync")
    unconfirmed = [a["text"] for a in b.get("assumptions", []) if not a["confirmed"]]
    if unconfirmed:
        r.warn(f"brief: {len(unconfirmed)} unconfirmed assumption(s)")


def all_claims(job, r):
    claims = {}
    for rel in RESEARCH_FILES + sorted(p.relative_to(_d(job)).as_posix() for p in (_d(job) / "research").glob("claims-rfi-*.json")):
        p = _d(job) / rel
        if not p.exists():
            continue
        data = load_json(p)
        for c in data.get("claims", []):
            if c["claim_id"] in claims:
                r.fail(f"duplicate claim id {c['claim_id']} ({rel})")
            claims[c["claim_id"]] = {**c, "_file": rel, "_desk": data.get("desk")}
    return claims


def g_research(job, r):
    expected = {"research/updates.json": ("updates", "patch-sentinel"),
                "research/claims-methods.json": ("claims", "methods-analyst"),
                "research/claims-quests.json": ("claims", "quest-archivist"),
                "research/claims-threats.json": ("claims", "threat-analyst"),
                "research/claims-logistics.json": ("claims", "logistics-analyst")}
    for rel, (schema, agent) in expected.items():
        data = _load(job, rel, r, schema)
        if data is None:
            continue
        _sealed(job, rel, r, required=False)
        check_provenance(job, rel, data, r, agent)
        pre = DESK_PREFIX.get(data.get("desk"))
        for c in data.get("claims", []):
            if pre and not c["claim_id"].startswith(f"C-{pre}-"):
                r.fail(f"{rel}: {c['claim_id']} does not use desk prefix C-{pre}-")
            tiers = {s["tier"] for s in c["sources"]}
            if tiers <= {"T4"}:
                r.warn(f"{c['claim_id']}: only T4 sources (lead, not evidence); verifier will reject unless upgraded")
            for s in c["sources"]:
                if "oldschool.runescape.wiki" in s["url"] and not s.get("revid"):
                    r.fail(f"{c['claim_id']}: wiki source without revid (pin it with tools/wiki.py)")
    claims = all_claims(job, r)
    r.ok(f"{len(claims)} claims across research files")
    upd = (_d(job) / "research/updates.json")
    if upd.exists():
        u = load_json(upd)
        ids = {c["claim_id"] for c in u.get("claims", [])}
        for it in u.get("items", []):
            for cid in it["claim_ids"]:
                if cid not in ids:
                    r.fail(f"updates {it['update_id']} references unknown claim {cid}")
        if len(u.get("sources_swept", [])) < 2:
            r.fail("patch-sentinel swept fewer than two independent sources")


def facts_index(job):
    p = _d(job) / "facts.json"
    return {f["fact_id"]: f for f in load_json(p)["facts"]} if p.exists() else {}


PART_FILES = {"updates": "research/updates.json", "methods": "research/claims-methods.json",
              "quests": "research/claims-quests.json", "threats": "research/claims-threats.json",
              "logistics": "research/claims-logistics.json"}


def g_facts(job, r, part=None, claim_range=None):
    rel = f"facts-parts/{part}.json" if part else "facts.json"
    fx = _load(job, rel, r, "facts")
    if not fx:
        return
    _sealed(job, rel, r, required=False)
    check_provenance(job, rel, fx, r, "fact-verifier")
    claims = all_claims(job, Report())
    if part:
        src = PART_FILES.get(part.split("-")[0])
        claims = {k: v for k, v in claims.items() if (v["_file"] == src if src else v["_file"].startswith("research/claims-rfi-"))}
    if claim_range:
        lo, hi = claim_range.split(":")
        key = lambda c: (c.rsplit("-", 1)[0], int(c.rsplit("-", 1)[1]))
        claims = {k: v for k, v in claims.items() if key(lo) <= key(k) <= key(hi)}
    entries = ledger.read_entries(job)
    seal_time = {}
    for e in entries:
        if e["event"] == "seal" and e["path"].startswith("research/"):
            seal_time.setdefault(e["path"], e["ts"][:10])
    ids = set()
    for f in fx["facts"]:
        if f["fact_id"] in ids:
            r.fail(f"duplicate fact id {f['fact_id']}")
        ids.add(f["fact_id"])
        c = claims.get(f["claim_id"])
        if c is None:
            r.fail(f"{f['fact_id']}: claim {f['claim_id']} not found in sealed research")
            continue
        if f["status"] in GOOD:
            if not any(s["tier"] in ("T1", "T2") for s in f["sources"]):
                r.fail(f"{f['fact_id']}: VERIFIED without any T1/T2 source")
            if not f.get("independent"):
                r.fail(f"{f['fact_id']}: VERIFIED without independent re-fetch")
            sealed_on = seal_time.get(c["_file"])
            if sealed_on and all(s["retrieved"][:10] < sealed_on for s in f["sources"]):
                r.fail(f"{f['fact_id']}: every verifier source predates the research seal; not independent")
            if json.dumps(f["value"], sort_keys=True) != json.dumps(c["value"], sort_keys=True):
                r.fail(f"{f['fact_id']}: value differs from researcher's claim but status is {f['status']} (must be DISPUTED)")
            if f.get("new_content") and f["status"] == "VERIFIED" and not f.get("caveat"):
                r.warn(f"{f['fact_id']}: new content verified without a caveat; wiki pages for new content change quickly")
    missing = set(claims) - {f["claim_id"] for f in fx["facts"]}
    if missing:
        r.fail(f"{len(missing)} claim(s) never adjudicated by the verifier: {sorted(missing)[:8]}")
    counts = {}
    for f in fx["facts"]:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    r.ok(f"fact statuses: {counts}")


def _refs(step):
    """Yield (path, {'value','fact'}) for every fact-backed number in a plan step."""
    for k in ("xp_per_action", "xp_per_hour", "est_hours"):
        if isinstance(step.get(k), dict):
            yield k, step[k]
    for i, s in enumerate(step.get("supplies_per_action", [])):
        yield f"supplies[{i}].qty", s["qty"]
    for i, s in enumerate(step.get("secondary_xp_per_action", [])):
        yield f"secondary[{i}].xp", s["xp"]
    for i, s in enumerate(step.get("xp_rewards", [])):
        yield f"xp_rewards[{i}]", s["xp"]
    for i, s in enumerate(step.get("lamp_rewards", [])):
        for k in ("xp", "xp_per_level"):
            if k in s:
                yield f"lamp[{i}].{k}", s[k]


def g_plan(job, r):
    plan = _load(job, "plan.json", r, "plan")
    if not plan:
        return
    _sealed(job, "plan.json", r, required=False)
    check_provenance(job, "plan.json", plan, r, "route-strategist")
    facts = facts_index(job)
    bp = _d(job) / "brief.json"
    if bp.exists():
        prof = load_json(bp)["profile"]
        exact = (prof.get("skill_xp") or {}).get(plan["target"]["skill"])
        if exact is not None and plan["start_xp"] != exact:
            r.fail(f"plan.start_xp {plan['start_xp']} differs from the verified {plan['target']['skill']} XP {exact} in the brief")
    step_ids = [s["step_id"] for s in plan["steps"]]
    if len(step_ids) != len(set(step_ids)):
        r.fail("plan: duplicate step ids")
    used = set()
    for st in plan["steps"]:
        for fid in st["facts"]:
            used.add(fid)
        for path, ref in _refs(st):
            f = facts.get(ref["fact"])
            if f is None:
                r.fail(f"{st['step_id']}.{path}: cites unknown fact {ref['fact']}")
                continue
            if f["status"] not in GOOD:
                r.fail(f"{st['step_id']}.{path}: cites {ref['fact']} with status {f['status']}")
            fv = f["value"]
            if isinstance(fv, dict):
                fv = fv.get("value", fv)
            if isinstance(fv, (int, float)) and abs(fv - ref["value"]) > 1e-9:
                r.fail(f"{st['step_id']}.{path}: plan says {ref['value']} but {ref['fact']} says {fv}")
            used.add(ref["fact"])
        for req in st.get("requirements", []):
            f = facts.get(req["fact"])
            if f is None or f["status"] not in GOOD:
                r.fail(f"{st['step_id']}: requirement cites unusable fact {req['fact']}")
            used.add(req["fact"])
        if st["kind"] == "train" and not (st.get("until_level") and st.get("xp_per_action") and st.get("xp_per_hour")):
            r.fail(f"{st['step_id']}: train step needs until_level, xp_per_action, xp_per_hour")
    for fid in used:
        f = facts.get(fid)
        if f is None:
            r.fail(f"plan cites unknown fact {fid}")
        elif f["status"] not in GOOD:
            r.fail(f"plan cites {fid} with status {f['status']}")
    in_routes = {sid for rt in plan["routes"] for sid in rt["step_ids"]}
    for sid in in_routes - set(step_ids):
        r.fail(f"route references unknown step {sid}")
    for sid in set(step_ids) - in_routes:
        r.warn(f"step {sid} is not used by any route")
    for dp in plan.get("decision_points", []):
        ids = [o["option_id"] for o in dp["options"]]
        if dp["recommended"] not in ids:
            r.fail(f"{dp['dp_id']}: recommended option {dp['recommended']} is not one of {ids}")
        for o in dp["options"]:
            for sid in o["step_ids"]:
                if sid not in step_ids:
                    r.fail(f"{dp['dp_id']}.{o['option_id']}: unknown step {sid}")
            for fid in o.get("facts", []):
                if fid not in facts or facts[fid]["status"] not in GOOD:
                    r.fail(f"{dp['dp_id']}.{o['option_id']}: cites unusable fact {fid}")
    if not plan.get("decision_points"):
        r.warn("plan has no decision points (the owner asked for next-step options with justification)")
    if not any(rt["route_id"] == "safest" for rt in plan["routes"]):
        r.fail("plan must always include a 'safest' route (Hardcore policy)")
    r.ok(f"plan: {len(step_ids)} steps, {len(plan['routes'])} routes, {len(used)} facts cited")


def g_calc(job, r):
    calc = _load(job, "calc.json", r)
    if not calc:
        return
    _sealed(job, "calc.json", r, required=False)
    if calc.get("plan_sha256") != sha256_file(_d(job) / "plan.json"):
        r.fail("calc.json was computed from a different plan.json; rerun tools/xp.py simulate")
    for rid, rt in calc["routes"].items():
        for e in rt["errors"]:
            r.fail(f"calc[{rid}]: {e}")
        for w in rt["warnings"]:
            r.warn(f"calc[{rid}]: {w}")
        r.ok(f"calc[{rid}]: level {rt['totals']['level_end']}, {rt['totals']['hours']} h")
    rv = _d(job) / "calc-review.json"
    if rv.exists():
        review = _load(job, "calc-review.json", r, "calc-review")
        if review and review["calc_sha256"] != sha256_file(_d(job) / "calc.json"):
            r.fail("calc-review.json reviewed a different calc.json")
        if review and review["decision"] != "pass":
            r.fail("quant review decision is not pass")
    else:
        r.fail("calc-review.json (quant sign-off) missing")


def g_risk(job, r):
    risk = _load(job, "risk.json", r, "risk")
    plan = load_json(_d(job) / "plan.json") if (_d(job) / "plan.json").exists() else None
    brief = load_json(_d(job) / "brief.json") if (_d(job) / "brief.json").exists() else None
    if not risk or not plan:
        return
    _sealed(job, "risk.json", r, required=False)
    check_provenance(job, "risk.json", risk, r, "risk-officer")
    facts = facts_index(job)
    by_step = {}
    for e in risk["entries"]:
        if e["step_id"] in by_step:
            r.fail(f"risk: duplicate entry for {e['step_id']}")
        by_step[e["step_id"]] = e
    for st in plan["steps"]:
        if st["step_id"] not in by_step:
            r.fail(f"risk: step {st['step_id']} has no danger assessment")
    hw = brief and brief["game_mode"]["world_type"] == "hardcore_worlds"
    informed = risk["risk_appetite"] == "informed"
    lad = danger.ladder()
    if not lad["calibrated"]:
        r.warn("danger scores are UNCALIBRATED (no approved game-relative ladder yet; run /osrs-calibrate)")
    for c in lad["conflicts"]:
        r.warn(f"calibration ordering conflict: {c}")
    entries = ledger.read_entries(job)
    accepted = {e["ref"] for e in entries if e["event"] == "accept_risk"}
    scores = {}
    plan_steps = {st["step_id"] for st in plan["steps"]}
    plan_routes = {rt["route_id"] for rt in plan["routes"]}
    for e in risk["entries"]:
        if e["step_id"] not in plan_steps:
            note = " (veto honoured: step removed from plan)" if e["verdict"] == "veto" else ""
            r.warn(f"risk {e['step_id']}: rated but no longer in the plan{note}")
            continue
        try:
            s = danger.assess(e, lad)
        except ValueError as exc:
            r.fail(f"risk {e['step_id']}: {exc}")
            continue
        scores[e["step_id"]] = s
        for fname in ("lethality", "pvp", "escape"):
            fac = e["factors"][fname]
            if fac["score"] > 0 and not fac.get("facts"):
                r.fail(f"risk {e['step_id']}.{fname}={fac['score']} without cited evidence")
            for fid in fac.get("facts", []):
                if fid not in facts or facts[fid]["status"] not in GOOD:
                    r.fail(f"risk {e['step_id']}.{fname} cites unusable fact {fid}")
        for m in e["mitigations"]:
            for fid in m.get("facts", []):
                if fid not in facts or facts[fid]["status"] not in GOOD:
                    r.fail(f"risk {e['step_id']} mitigation {m['id']} cites unusable fact {fid}")
        hwc = e["hw_death_classification"]
        if hw and hwc["status"] == "SAFE_DEATH" and not hwc.get("facts"):
            r.fail(f"risk {e['step_id']}: claims a SAFE death on Hardcore Worlds without evidence")
        if hw and "HW_UNSAFE_ACTIVITY" in e["flags"] and hwc["status"] == "SAFE_DEATH":
            r.fail(f"risk {e['step_id']}: flagged HW_UNSAFE_ACTIVITY yet classified SAFE_DEATH")
        if e["verdict"] == "veto":
            if informed and not e.get("veto_basis"):
                r.fail(f"risk {e['step_id']}: veto without veto_basis; in informed mode danger alone never vetoes")
            r.fail(f"risk {e['step_id']}: VETOED by risk officer ({e.get('veto_basis', 'danger')}): {e.get('verdict_reason', '')}")
        if s["residual_tier"] in ("Critical", "Extreme") and e["step_id"] not in accepted and not informed:
            r.fail(f"risk {e['step_id']}: residual {s['residual_tier']} ({s['residual_ds']}) needs the user's explicit acceptance")
        if any(f in ("WILDERNESS", "DEEP_WILDERNESS", "PVP_HOTSPOT") for f in e["flags"]) and not e.get("wilderness_level"):
            r.fail(f"risk {e['step_id']}: Wilderness step without wilderness_level (needed for the owner's tiered premium)")
        if s["inherent_ds"] >= danger.PREP_CARD_FROM:
            pre = e.get("preconditions", {})
            missing = [k for k, ok in (("mitigations", e["mitigations"]), ("stop_conditions", pre.get("stop_conditions")),
                                       ("min_hitpoints", pre.get("min_hitpoints")), ("bailout", e.get("bailout")),
                                       ("necessity", e.get("necessity"))) if not ok]
            if missing:
                r.fail(f"risk {e['step_id']}: score {s['inherent_ds']} (unmitigated) needs a complete prep card; missing {missing}")
    cap = danger.APPETITE_CAPS[risk["risk_appetite"]]
    for rt in plan["routes"]:
        worst = max((scores[s]["residual_ds"] for s in rt["step_ids"] if s in scores), default=0)
        over = [s for s in rt["step_ids"] if s in scores and scores[s]["residual_ds"] > cap]
        if rt["route_id"] == "safest" and over and not informed:
            unaccepted = [s for s in over if s not in accepted]
            if unaccepted:
                r.fail(f"safest route has step(s) above the {risk['risk_appetite']} cap {cap} with no accepted risk: {unaccepted}")
        r.ok(f"route {rt['route_id']}: worst residual DS {worst} ({danger.tier(worst)})")
    for rv in risk["route_verdicts"]:
        if rv["verdict"] == "veto":
            if rv["route_id"] in plan_routes:
                r.fail(f"risk officer vetoed route {rv['route_id']}")
            else:
                r.warn(f"route {rv['route_id']} vetoed and removed from the plan (veto honoured)")


def g_redteam(job, r):
    rt = _load(job, "redteam.json", r, "redteam")
    if not rt:
        return
    _sealed(job, "redteam.json", r, required=False)
    check_provenance(job, "redteam.json", rt, r, "red-team")
    for f in rt["findings"]:
        if f["status"] == "open" and f["severity"] in ("critical", "high"):
            r.fail(f"red-team {f['finding_id']} ({f['severity']}) is still open: {f['scenario'][:90]}")
        elif f["status"] == "open":
            r.warn(f"red-team {f['finding_id']} ({f['severity']}) open")
    r.ok(f"red-team: {len(rt['findings'])} finding(s) reviewed")


def g_prose(job, r):
    pr = _load(job, "prose.json", r, "prose")
    plan = load_json(_d(job) / "plan.json") if (_d(job) / "plan.json").exists() else None
    if not pr or not plan:
        return
    _sealed(job, "prose.json", r, required=False)
    check_provenance(job, "prose.json", pr, r, "guide-author")
    have = {s["step_id"] for s in pr["steps"]}
    for st in plan["steps"]:
        if st["step_id"] not in have:
            r.fail(f"prose: step {st['step_id']} has no text")
    facts = facts_index(job)

    def scan(text, where):
        stripped = re.sub(r"\{\{[^}]*\}\}", "", text)
        stripped = re.sub(r"`[^`]*`", "", stripped)
        if re.search(r"\d", stripped):
            r.fail(f"prose {where}: bare number in text (numbers must be {{tokens}} or `item names`): {text[:80]!r}")
        for tok in re.findall(r"\{\{[^}]*\}\}", text):
            if not TOKEN_RE.fullmatch(tok):
                r.fail(f"prose {where}: unknown token {tok}")
            m = re.search(r"fact:(F-\d{4})", tok)
            if m and (m.group(1) not in facts or facts[m.group(1)]["status"] not in GOOD):
                r.fail(f"prose {where}: token cites unusable fact {m.group(1)}")

    for key in ("intro", "outro"):
        if pr.get(key):
            scan(pr[key], key)
    for s in pr["steps"]:
        for k in ("summary",):
            scan(s[k], f"{s['step_id']}.{k}")
        for k in ("instructions", "tips", "warnings"):
            for i, t in enumerate(s.get(k, [])):
                scan(t, f"{s['step_id']}.{k}[{i}]")


def g_content(job, r):
    c = _load(job, "content.json", r)
    if not c:
        return
    _sealed(job, "content.json", r, required=False)
    for rel in ("plan.json", "risk.json", "facts.json", "prose.json", "calc.json"):
        want = c.get("inputs", {}).get(rel)
        if want != sha256_file(_d(job) / rel):
            r.fail(f"content.json was assembled from a different {rel}")
    r.ok("content.json inputs match current sealed artifacts")


def g_html(job, r):
    p = _d(job) / "guide.html"
    if not p.exists():
        r.fail("guide.html missing")
        return
    html = p.read_text(encoding="utf-8")
    m = re.search(r'<meta name="content-sha256" content="([0-9a-f]{64})"', html)
    if not m or m.group(1) != sha256_file(_d(job) / "content.json"):
        r.fail("guide.html does not embed the current content.json hash")
    else:
        r.ok("guide.html embeds current content hash")
    m = re.search(r'<script type="application/json" id="guide-data">(.*?)</script>', html, re.S)
    if not m:
        r.fail("guide.html has no embedded guide data")
    else:
        embedded = json.loads(m.group(1).replace("<\\/", "</"))
        if embedded != load_json(_d(job) / "content.json"):
            r.fail("embedded guide data differs from content.json (renderer altered content)")
        else:
            r.ok("embedded data identical to content.json")
    ext = re.findall(r'<(?:script|link)[^>]+(?:src|href)="(https?://[^"]+)"', html)
    bad = [u for u in ext if not u.startswith("https://fonts.googleapis.com")]
    if bad:
        r.fail(f"guide.html loads external resources: {bad}")


def g_release(job, r):
    for g in (g_brief, g_research, g_facts, g_plan, g_calc, g_risk, g_redteam, g_prose, g_content, g_html):
        g(job, r)
    for rel in ("brief.json", "facts.json", "plan.json", "calc.json", "calc-review.json", "risk.json",
                "redteam.json", "prose.json", "content.json"):
        _sealed(job, rel, r, required=True)
    for p in ledger.verify(job):
        (r.warn if p.startswith("unsealed") else r.fail)(p)
    rs = ledger.release_status(job)
    if not rs["released"]:
        r.warn("not yet released: " + "; ".join(rs["reasons"]))


STAGES = {"brief": g_brief, "research": g_research, "facts": g_facts, "plan": g_plan, "calc": g_calc,
          "risk": g_risk, "redteam": g_redteam, "prose": g_prose, "content": g_content, "html": g_html,
          "release": g_release, "all": g_release}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("job")
    p.add_argument("stage", choices=list(STAGES))
    p.add_argument("--part", help="facts stage only: check facts-parts/<desk>[-x].json against that desk's claims")
    p.add_argument("--claims", help="facts stage only: restrict to a claim-id range, e.g. C-QST-001:C-QST-134")
    a = p.parse_args()
    r = Report()
    if a.stage == "facts" and a.part:
        g_facts(a.job, r, a.part, a.claims)
    else:
        STAGES[a.stage](a.job, r)
    r.print()
    sys.exit(1 if r.fails else 0)


if __name__ == "__main__":
    main()
