#!/usr/bin/env python3
"""Render the interactive guide: content.json + templates/guide.html -> guide.html.

The renderer adds nothing to the content. It embeds content.json byte-for-byte
as JSON (validate.py `html` proves it), stamps the content hash and release
state, and attaches the audit summary. Unless the ledger shows a QA approval
of this exact content.json, the page carries a NOT RELEASED banner.

  python3 tools/render.py <job> [--out guide.html]
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import TEMPLATES, die, job_dir, load_json, sha256_file  # noqa: E402
import audit  # noqa: E402
import ledger  # noqa: E402


def embed(obj) -> str:
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("job")
    p.add_argument("--out", default="guide.html")
    a = p.parse_args()
    d = job_dir(a.job)
    cpath = d / "content.json"
    if not cpath.exists():
        die("content.json missing; run tools/assemble.py first")
    content = load_json(cpath)
    chash = sha256_file(cpath)
    st = ledger.seal_state(ledger.read_entries(a.job)).get("content.json")
    if not st or not st["sealed"] or st["sha256"] != chash:
        die("content.json must be sealed (author system) and unchanged before rendering")
    summary = audit.summary(a.job)
    tpl = (TEMPLATES / "guide.html").read_text(encoding="utf-8")
    out = (tpl.replace("__CONTENT_SHA256__", chash)
              .replace("__RELEASE_STATE__", "released" if summary["release"]["released"] else "draft")
              .replace("__TITLE__", html.escape(content["meta"]["title"]))
              .replace("__GUIDE_DATA__", embed(content))
              .replace("__AUDIT_DATA__", embed(summary)))
    (d / a.out).write_text(out, encoding="utf-8")
    print(f"rendered {d / a.out} ({'RELEASED' if summary['release']['released'] else 'DRAFT'}; content {chash[:16]})")


if __name__ == "__main__":
    main()
