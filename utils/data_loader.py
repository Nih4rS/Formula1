from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import json

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
DATA_ROOT.mkdir(parents=True, exist_ok=True)

AUTO_BUILD_MIN_YEAR = 2020
_auto_build_running = False


def _auto_populate_missing_years() -> None:
    """Ensure data exists for every season from AUTO_BUILD_MIN_YEAR onward."""
    global _auto_build_running
    if _auto_build_running:
        return

    try:
        existing = {
            int(p.name)
            for p in DATA_ROOT.iterdir()
            if p.is_dir() and p.name.isdigit()
        }
    except FileNotFoundError:
        existing = set()

    current_year = max(datetime.now().year, AUTO_BUILD_MIN_YEAR)
    target_years = [
        year for year in range(AUTO_BUILD_MIN_YEAR, current_year + 1)
        if year not in existing
    ]
    if not target_years:
        return

    try:
        from etl.build_all import build
    except Exception as exc:
        print(f"[auto-build] Unable to import builder: {exc}")
        return

    _auto_build_running = True
    try:
        for year in target_years:
            try:
                print(f"[auto-build] Building telemetry for {year}")
                build(year, year)
            except Exception as err:
                print(f"[auto-build] Failed building {year}: {err}")
    finally:
        _auto_build_running = False


def _list_dirs(path: Path) -> List[str]:
    if not path.exists():
        return []
    return sorted([p.name for p in path.iterdir() if p.is_dir()])


def list_years() -> List[str]:
    _auto_populate_missing_years()
    # Try DuckDB-backed listing first
    try:
        from utils.db import list_years_db
        years = list_years_db()
        if years:
            return years
    except Exception:
        pass
    return _list_dirs(DATA_ROOT)


def list_events(year: str) -> List[str]:
    try:
        from utils.db import list_events_db
        evs = list_events_db(year)
        if evs:
            return evs
    except Exception:
        pass
    return _list_dirs(DATA_ROOT / year)


def list_sessions(year: str, event: str) -> List[str]:
    try:
        from utils.db import list_sessions_db
        sess = list_sessions_db(year, event)
        if sess:
            return sess
    except Exception:
        pass
    return _list_dirs(DATA_ROOT / year / event)


def list_drivers(year: int | str, event: str | None, session: str | None) -> list[str]:
    """List driver codes that have *_bestlap.json for the given triplet.
    Returns [] if year/event/session is missing or the dir doesn't exist.
    """
    if not (year and event and session):
        return []

    # Try DB first
    try:
        from utils.db import list_drivers_db
        drivers_db = list_drivers_db(year, event, session)
        if drivers_db:
            return drivers_db
    except Exception:
        pass

    p = DATA_ROOT / str(year) / event / session
    if not p.exists():
        return []

    drivers: set[str] = set()
    for f in p.glob("*_bestlap.json"):
        # filename pattern "XXX_bestlap.json"
        name = f.stem
        if name.endswith("_bestlap"):
            drivers.add(name[:-8])  # strip "_bestlap"
    return sorted(drivers)


def load_lap(year: str, event: str, session: str, driver: str) -> Dict[str, Any]:
    fp = DATA_ROOT / year / event / session / f"{driver}_bestlap.json"
    if not fp.exists():
        raise FileNotFoundError(f"Missing lap JSON: {fp}")
    with open(fp, "r", encoding="utf-8") as f:
        j = json.load(f)
    # minimal schema validation
    for k in ["distance_m", "cum_lap_time_s", "speed_kph"]:
        if k not in j or not isinstance(j[k], list):
            raise ValueError(f"Malformed JSON at {fp}: missing {k}")
    return j
