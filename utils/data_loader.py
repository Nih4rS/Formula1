from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import json

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


def _list_dirs(path: Path) -> List[str]:
    if not path.exists():
        return []
    return sorted([p.name for p in path.iterdir() if p.is_dir()])


def list_years() -> List[str]:
    return _list_dirs(DATA_ROOT)


def list_events(year: str) -> List[str]:
    return _list_dirs(DATA_ROOT / year)


def list_sessions(year: str, event: str) -> List[str]:
    return _list_dirs(DATA_ROOT / year / event)


def list_drivers(year: int | str, event: str | None, session: str | None) -> list[str]:
    """List driver codes that have *_bestlap.json for the given triplet.
    Returns [] if year/event/session is missing or the dir doesn't exist.
    """
    if not (year and event and session):
        return []

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
