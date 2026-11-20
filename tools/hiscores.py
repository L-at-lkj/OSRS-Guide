#!/usr/bin/env python3
"""Account-stat verification for the Intake Officer.

Minimal trust applies to the client brief too: stated levels are checked
against an independent record where one exists. The result records which
source confirmed each number; unconfirmed stats stay marked `user_stated`.

Commands
  lookup PLAYER [--mode MODE | --suffix SUFFIX]
      Official hiscores. MODE defaults to hardcore_worlds (board
      m=hiscore_oldschool_hardcore_mains): Hardcore Worlds progress does NOT
      appear on the normal board, so a Hardcore Worlds character must be
      checked here. Other modes: normal, ironman, hardcore_ironman, ultimate,
      deadman, seasonal, fresh_start. --suffix overrides the board.
      Hiscores refresh on logout, so in-game screenshots can be newer; use
      the more recent source and record both.
  wikisync PLAYER [--profile STANDARD]
      WikiSync (RuneLite plugin data): levels plus quest and diary completion,
      only if the player has the WikiSync plugin enabled.

Player names are sent only to these official/wiki endpoints, and only
because the account owner asked for their own account to be checked.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import die, now_iso  # noqa: E402

MODES = {"hardcore_worlds": "_hardcore_mains", "normal": "", "ironman": "_ironman", "hardcore_ironman": "_hardcore_ironman", "ultimate": "_ultimate",
         "deadman": "_deadman", "seasonal": "_seasonal", "fresh_start": "_fresh_start"}
UA = "osrs-guide-company/1.0 (personal guide tooling)"


def get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as exc:
        die(f"request failed ({exc}); the host may need to be allowed in this environment")


def cmd_lookup(a):
    suffix = a.suffix if a.suffix is not None else MODES[a.mode]
    url = (f"https://secure.runescape.com/m=hiscore_oldschool{suffix}/index_lite.json?player="
           + urllib.parse.quote(a.player))
    data = get(url)
    stats = {s["name"]: s["level"] for s in data.get("skills", []) if s.get("level", -1) > 0 and s["name"] != "Overall"}
    xp = {s["name"]: s.get("xp") for s in data.get("skills", []) if s["name"] != "Overall"}
    print(json.dumps({"source": "official_hiscores", "board": a.mode if a.suffix is None else a.suffix,
                      "endpoint": url.split("?")[0], "retrieved": now_iso(),
                      "player": a.player, "stats": stats, "xp": xp}, indent=2))


def cmd_wikisync(a):
    url = f"https://sync.runescape.wiki/runelite/player/{urllib.parse.quote(a.player)}/{a.profile}"
    data = get(url)
    quests = data.get("quests", {})
    print(json.dumps({"source": "wikisync", "retrieved": now_iso(), "player": a.player,
                      "stats": data.get("levels", {}),
                      "quests_completed": sorted(q for q, v in quests.items() if v == 2),
                      "quests_started": sorted(q for q, v in quests.items() if v == 1),
                      "diaries": data.get("achievement_diaries", {})}, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("lookup"); s.add_argument("player"); s.add_argument("--mode", choices=list(MODES), default="hardcore_worlds")
    s.add_argument("--suffix"); s.set_defaults(f=cmd_lookup)
    s = sp.add_parser("wikisync"); s.add_argument("player"); s.add_argument("--profile", default="STANDARD"); s.set_defaults(f=cmd_wikisync)
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
