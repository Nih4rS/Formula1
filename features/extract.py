# features/extract.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import warnings

import pandas as pd
import fastf1

from utils.events import slug_to_event_name

warnings.filterwarnings("ignore", category=FutureWarning)


@dataclass
class SessionFeatures:
    year: int
    event_slug: str
    session_code: str
    frame: pd.DataFrame  # columns: Driver, Team, Grid, QPos, TargetPos


def _qualifying_positions(year: int, event_slug: str) -> pd.DataFrame:
    """Return DataFrame with Driver -> Qualifying position if available."""
    try:
        sess = fastf1.get_session(year, slug_to_event_name(event_slug), "Q")
        sess.load(results=True, laps=False, telemetry=False, weather=False)
        res = sess.results
    except Exception:
        res = None
    if res is None or res.empty:
        return pd.DataFrame(columns=["Driver", "QPos"])  # empty
    df = res.copy()
    # Some FastF1 columns: Abbreviation or Driver
    drv = df.get("Abbreviation") if "Abbreviation" in df.columns else df.get("Driver")
    out = pd.DataFrame({
        "Driver": drv,
        "QPos": df["Position"].astype(int)
    })
    out = out.dropna(subset=["Driver"]).reset_index(drop=True)
    out["Driver"] = out["Driver"].astype(str)
    return out


def extract_session_features(year: int, event_slug: str, session_code: str = "R") -> SessionFeatures:
    """Build a simple feature set for a session (default Race).

    Features (per driver):
      - Grid: starting grid position (int, NaN -> large fallback)
      - QPos: qualifying position (if available)
    Target (for Race):
      - TargetPos = finish position
    """
    session = fastf1.get_session(year, slug_to_event_name(event_slug), session_code)
    session.load(results=True, laps=False, telemetry=False, weather=False)
    res = session.results
    if res is None or res.empty:
        return SessionFeatures(year, event_slug, session_code, pd.DataFrame())

    df = res.copy()
    drv = df.get("Abbreviation") if "Abbreviation" in df.columns else df.get("Driver")
    out = pd.DataFrame({
        "Driver": drv.astype(str),
        "Team": (df.get("TeamName") or df.get("Team")).astype(str) if ("TeamName" in df.columns or "Team" in df.columns) else "",
        "Grid": pd.to_numeric(df.get("GridPosition"), errors="coerce"),
        "TargetPos": pd.to_numeric(df.get("Position"), errors="coerce"),
    })

    # Merge qualifying
    q = _qualifying_positions(year, event_slug)
    if not q.empty:
        out = out.merge(q, on="Driver", how="left")
    else:
        out["QPos"] = pd.NA

    # Fallbacks for missing numeric values
    out["Grid"] = out["Grid"].fillna(40).astype(float)
    out["QPos"] = out["QPos"].fillna(40).astype(float)
    out["TargetPos"] = out["TargetPos"].astype(float)

    return SessionFeatures(year, event_slug, session_code, out)


def build_training_frame(year_start: int, year_end: int) -> pd.DataFrame:
    """Aggregate race features across a range of seasons.

    Skips sessions that fail to load.
    """
    rows: List[pd.DataFrame] = []
    for y in range(year_start, year_end + 1):
        try:
            sched = fastf1.get_event_schedule(y, include_testing=False)
        except Exception:
            sched = None
        if sched is None or sched.empty:
            continue
        for _, ev in sched.iterrows():
            ev_slug = str(ev["EventName"]).strip()
            # Extract for Race only
            try:
                pack = extract_session_features(y, ev_slug, "R")
            except Exception:
                continue
            if not pack.frame.empty:
                fr = pack.frame.copy()
                fr.insert(0, "Year", y)
                fr.insert(1, "Event", ev_slug)
                rows.append(fr)
    if not rows:
        return pd.DataFrame()
    big = pd.concat(rows, ignore_index=True)
    return big
