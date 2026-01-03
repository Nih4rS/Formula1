from __future__ import annotations
"""
Lightweight data refresher:
- Ensures folder structure exists for all scheduled sessions for a year range
- Writes drivers.json for each loaded session so selectors can populate
- Does not download heavy telemetry by default (best laps come from build_all if desired)

Run:
  python etl/refresh_data.py --from 2024 --to 2025
Defaults to current year and previous year.
"""

import argparse
from datetime import datetime
from pathlib import Path
import json
import sys

import pandas as pd
import fastf1

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

fastf1.Cache.enable_cache(ROOT / "fastf1_cache")

from utils.events import event_name_to_slug


def ensure_session(year: int, event_name: str, session_code: str) -> None:
    slug = event_name_to_slug(event_name)
    dest = DATA / str(year) / slug / session_code
    dest.mkdir(parents=True, exist_ok=True)

    # Try to fetch drivers for this session to write a small metadata file.
    try:
        ses = fastf1.get_session(year, event_name, session_code)
        ses.load(laps=True, telemetry=False, weather=False)
        laps = ses.laps
        if laps is None or laps.empty:
            return
        df = laps[["Driver", "Team"]].dropna().drop_duplicates()
        payload = {row.Driver: {"Team": row.Team} for _, row in df.iterrows()}
        (dest / "drivers.json").write_text(json.dumps(payload, ensure_ascii=False, indent=0), encoding="utf-8")
    except Exception:
        # Non-fatal: we still created the session folder
        pass


def refresh(year_from: int, year_to: int) -> None:
    for year in range(year_from, year_to + 1):
        try:
            sched = fastf1.get_event_schedule(year, include_testing=False)
        except Exception as exc:
            print(f"[refresh] schedule error {year}: {exc}")
            continue
        if sched is None or sched.empty:
            continue
        for _, ev in sched.iterrows():
            evname = str(ev.get("EventName", ""))
            for code in ["FP1", "FP2", "FP3", "SQ", "SS", "Q", "R"]:
                ensure_session(year, evname, code)

    # Rebuild the database so schedule + drivers metadata is indexed
    try:
        from etl.build_db import build
        build(reset=True)
    except Exception as exc:
        print("[refresh] DB build failed:", exc)


def main(argv: list[str]) -> int:
    curr = datetime.utcnow().year
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="year_from", type=int, default=curr - 1)
    parser.add_argument("--to", dest="year_to", type=int, default=curr)
    args = parser.parse_args(argv)
    refresh(args.year_from, args.year_to)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
