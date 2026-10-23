#!/usr/bin/env python3
"""Combine the JSON files in data/ into data.js, which the site loads.

Usage: python3 scripts/build_data.py
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


bundle = {
    "teams": load("teams"),
    "schedule": load("schedule"),
    "weekly_stats": load("weekly_stats"),
    "sample_stats": load("sample_stats"),
    "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
}

js = (
    "/* Wintris league data. Built by scripts/build_data.py, do not edit by hand. */\n"
    "window.WINTRIS_DATA = " + json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + ";\n"
)
(ROOT / "data.js").write_text(js, encoding="utf-8")
weeks = sorted({r["week"] for r in bundle["weekly_stats"] if r.get("week", 0) >= 1})
print(f"data.js written: {len(bundle['teams'])} teams, finished weeks {weeks or 'none yet'}")
