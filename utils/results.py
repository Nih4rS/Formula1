from __future__ import annotations
from pathlib import Path
from typing import Optional

import pandas as pd
import fastf1

from utils.events import slug_to_event_name

# Reuse the same FastF1 cache as other modules
CACHE = Path("fastf1_cache")
CACHE.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(CACHE)


def get_race_results(year: int, event_slug: str) -> pd.DataFrame:
    """Return official race classification table for the selected GP.

    Columns: Position, Driver, Team, Grid, Points, Status
    """
    event_name = slug_to_event_name(event_slug)
    ses = fastf1.get_session(int(year), event_name, "R")
    # Load minimal to get results; no need for telemetry or laps here
    ses.load(telemetry=False, weather=False, laps=False)
    if getattr(ses, "results", None) is None:
        return pd.DataFrame()
    df = ses.results
    # Harmonize columns
    out = pd.DataFrame({
        "Position": df.get("Position", pd.Series(range(1, len(df) + 1))).astype(int),
        "Driver": df.get("Abbreviation", df.get("DriverNumber", pd.Series([None]*len(df)))).astype(str),
        "Team": df.get("TeamName", pd.Series([None]*len(df))),
        "Grid": df.get("GridPosition", pd.Series([None]*len(df))),
        "Points": df.get("Points", pd.Series([0]*len(df))),
        "Status": df.get("Status", pd.Series([None]*len(df))),
    }).sort_values("Position").reset_index(drop=True)
    return out


def get_lap_times(year: int, event_slug: str, driver: Optional[str] = None) -> pd.DataFrame:
    """Return per-lap times for the race. If driver is provided, filter to that driver.

    Columns: LapNumber, Driver, LapTime, Sector1Time, Sector2Time, Sector3Time, Compound, TyreLife, PitOut, PitIn
    """
    event_name = slug_to_event_name(event_slug)
    ses = fastf1.get_session(int(year), event_name, "R")
    ses.load(laps=True, telemetry=False, weather=False)
    laps = ses.laps
    if laps is None or laps.empty:
        return pd.DataFrame()
    cols = [
        "LapNumber", "Driver", "LapTime", "Sector1Time", "Sector2Time", "Sector3Time",
        "Compound", "TyreLife", "PitOutTime", "PitInTime"
    ]
    df = laps[cols].copy()
    if driver:
        df = df[df["Driver"] == driver]
    # Convert timedeltas to seconds for easier charting
    def td_to_s(x):
        try:
            return x.total_seconds()
        except Exception:
            return None
    for c in ["LapTime", "Sector1Time", "Sector2Time", "Sector3Time"]:
        if c in df.columns:
            df[c + "_s"] = df[c].map(td_to_s)
    return df.reset_index(drop=True)


def get_session_results(year: int, event_slug: str, session_code: str) -> pd.DataFrame:
    """Return official classification for any session code (FP1/FP2/FP3/SQ/SPR/Q/R).

    Always includes Position, Driver, Team when available. Adds common timing columns if present.
    """
    event_name = slug_to_event_name(event_slug)
    ses = fastf1.get_session(int(year), event_name, session_code)
    # light load to fetch results only
    ses.load(telemetry=False, weather=False, laps=False)
    if getattr(ses, "results", None) is None:
        return pd.DataFrame()
    df = ses.results

    # Start with core columns
    out = pd.DataFrame({
        "Position": df.get("Position", pd.Series(range(1, len(df) + 1))).astype(int),
        "Driver": df.get("Abbreviation", df.get("DriverNumber", pd.Series([None]*len(df)))).astype(str),
        "Team": df.get("TeamName", pd.Series([None]*len(df))),
    })
    # Add optional time/points columns if available
    optional_cols = [
        ("Time", "Time"),
        ("Q1", "Q1"), ("Q2", "Q2"), ("Q3", "Q3"),
        ("Points", "Points"),
        ("Grid", "GridPosition"),
        ("Status", "Status"),
    ]
    for out_name, src in optional_cols:
        if src in df.columns:
            out[out_name] = df[src]
    return out.sort_values("Position").reset_index(drop=True)
