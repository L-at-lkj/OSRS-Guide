#!/usr/bin/env python3
"""Hardcore Worlds GE price snapshot (no agent needed: mechanical, sourced, sealed).

Source: the OSRS Wiki real-time prices API for the Hardcore Worlds economy,
https://prices.runescape.wiki/api/v2/osrs-hc/{latest,mapping,volumes} (the data
behind https://prices.runescape.wiki/osrs-hc). Main-game prices are NOT used.

  python3 tools/prices.py snapshot <job> --item "Amylase crystal" --item "Monkfish" ...
  python3 tools/prices.py lookup "Amylase crystal"

The snapshot (jobs/<job>/prices.json, sealed by `system`) records, per item:
id, instant-buy (high) and instant-sell (low) prices with their timestamps,
the mid price used for calculations, 24h volume and a `thin_market` flag.
A new economy is thin: the guide shows prices with their timestamp and flags
any item with low volume.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import die, job_dir, now_iso, save_json  # noqa: E402

BASE = "https://prices.runescape.wiki/api/v2/osrs-hc"
UA = "osrs-companion/1.0 (personal guide tooling)"
THIN_VOLUME = 500  # items traded per day below which the market is flagged as thin


def get(path: str):
    req = urllib.request.Request(f"{BASE}/{path}", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as exc:
        die(f"price API request failed ({exc}); prices.runescape.wiki must be reachable")


def resolve(names: list[str]) -> dict[str, dict]:
    mapping = get("mapping")
    mapping = mapping if isinstance(mapping, list) else mapping.get("data", [])
    by_name = {m["name"].lower(): m for m in mapping}
    out = {}
    for n in names:
        m = by_name.get(n.lower())
        if not m:
            die(f"item not found in the Hardcore Worlds price mapping: {n!r}")
        out[n] = m
    return out


def cmd_snapshot(a):
    items = resolve(a.item)
    latest = get("latest").get("data", {})
    vol = get("volumes")
    vol = vol.get("data", vol) if isinstance(vol, dict) else {}
    snap = {"source": f"{BASE}/latest (+/mapping, /volumes)", "economy": "Hardcore Worlds (osrs-hc)",
            "retrieved": now_iso(), "tier": "T2", "thin_volume_threshold": THIN_VOLUME, "items": {}}
    for name, m in items.items():
        p = latest.get(str(m["id"]), {})
        hi, lo = p.get("high"), p.get("low")
        mid = round((hi + lo) / 2) if hi and lo else (hi or lo)
        v = vol.get(str(m["id"])) if isinstance(vol, dict) else None
        snap["items"][name] = {"id": m["id"], "high": hi, "high_time": p.get("highTime"), "low": lo,
                               "low_time": p.get("lowTime"), "mid": mid, "volume_24h": v,
                               "thin_market": (v is None or v < THIN_VOLUME), "limit": m.get("limit"),
                               "tradeable_on_ge": True}
    save_json(job_dir(a.job) / "prices.json", snap)
    for n, x in snap["items"].items():
        print(f"{n:28s} mid {x['mid']!s:>9}  vol24h {x['volume_24h']!s:>8}  {'THIN' if x['thin_market'] else ''}")


def cmd_lookup(a):
    m = resolve([a.name])[a.name]
    p = get("latest").get("data", {}).get(str(m["id"]), {})
    print(json.dumps({"name": a.name, "id": m["id"], **p}, indent=1))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("snapshot"); s.add_argument("job"); s.add_argument("--item", action="append", required=True); s.set_defaults(f=cmd_snapshot)
    s = sp.add_parser("lookup"); s.add_argument("name"); s.set_defaults(f=cmd_lookup)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
