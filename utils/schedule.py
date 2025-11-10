# utils/schedule.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import fastf1

# Ensure FastF1 cache is on (same cache folder your ETL uses)
from pathlib import Path
from utils.events import slug_to_event_name

CACHE = Path("fastf1_cache")
CACHE.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(CACHE)

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"

_SESSION_ORDER = ["FP1", "FP2", "FP3", "SS", "SQ", "SPR", "Q", "R"]
_SESSION_FRIENDLY = {
    "FP1": "Free Practice 1",
    "FP2": "Free Practice 2",
    "FP3": "Free Practice 3",
    "SS": "Sprint Shootout",
    "SQ": "Sprint Qualifying",
    "SPR": "Sprint",
    "Q": "Qualifying",
    "R": "Race",
}

# FastF1 schedule dataframe uses column names like QualifyingDate, RaceDate etc;
# Provide explicit mapping from session code to schedule column.
_CODE_TO_COL = {
    "FP1": "FP1Date",
    "FP2": "FP2Date",
    "FP3": "FP3Date",
    "Q": "QualifyingDate",
    "R": "RaceDate",
    "SS": "SprintShootoutDate",  # 2023+ format
    "SQ": "SprintQualifyingDate",  # legacy naming (pre shootout change)
    "SPR": "SprintDate",
}

def _localize(ts_utc: Optional[pd.Timestamp]) -> Optional[pd.Timestamp]:
    if ts_utc is None or pd.isna(ts_utc):
        return None
    if ts_utc.tzinfo is None:
        ts_utc = ts_utc.tz_localize("UTC")
    return ts_utc.tz_convert(None).to_pydatetime().astimezone()  # system local tz


def fetch_schedule(year: int) -> pd.DataFrame:
    """Return tidy schedule with one row per session and both UTC and Local times.

    This version fixes earlier incorrect usage of non-existent columns like 'QDate'.
    We rely on explicit mapping of session codes to the correct FastF1 schedule
    DataFrame column names (e.g. 'QualifyingDate', 'RaceDate'). If a column is
    missing or NaT, we treat the session as unavailable.
    """
    try:
        sched = fastf1.get_event_schedule(year, include_testing=False)
    except Exception:
        sched = None

    if sched is None or sched.empty:
        return _fallback_schedule(year)

    rows = []
    for _, ev in sched.iterrows():
        event = str(ev.get("EventName", "")).strip()
        country = str(ev.get("Country", ""))
        location = str(ev.get("Location", ""))
        for code, col in _CODE_TO_COL.items():
            if col not in ev or pd.isna(ev[col]):
                continue
            try:
                ts_utc = pd.to_datetime(ev[col], utc=True, errors="coerce")
            except Exception:
                ts_utc = None
            if ts_utc is None or pd.isna(ts_utc):
                continue
            rows.append({
                "Year": year,
                "EventName": event,
                "Country": country,
                "Location": location,
                "SessionCode": code,
                "Session": _SESSION_FRIENDLY.get(code, code),
                "StartUTC": ts_utc.to_pydatetime(),
                "StartLocal": _localize(ts_utc)
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return _fallback_schedule(year)
    cat = pd.Categorical(df["SessionCode"], categories=_SESSION_ORDER, ordered=True)
    df = df.assign(SessionOrder=cat).sort_values(["EventName", "SessionOrder"]).reset_index(drop=True)
    return df.drop(columns=["SessionOrder"])


def next_session(df: pd.DataFrame, now: datetime | None = None) -> Optional[pd.Series]:
    if df.empty:
        return None
    now = now or datetime.now(timezone.utc)
    mask = pd.to_datetime(df["StartUTC"], utc=True) > now
    if not mask.any():
        return None
    return df.loc[mask].iloc[0]


def countdown_str(target_utc: datetime) -> str:
    now = datetime.now(timezone.utc)
    delta = target_utc.replace(tzinfo=timezone.utc) - now
    if delta.total_seconds() <= 0:
        return "live/finished"
    s = int(delta.total_seconds())
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d: parts.append(f"{d}d")
    parts.append(f"{h}h")
    parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)


def _fallback_schedule(year: int) -> pd.DataFrame:
    """Derive a minimal schedule from local data files when FastF1 fetch fails."""
    year_dir = DATA_ROOT / str(year)
    if not year_dir.exists():
        return pd.DataFrame()

    rows = []
    for event_dir in sorted([p for p in year_dir.iterdir() if p.is_dir()]):
        event_slug = event_dir.name
        event_name = slug_to_event_name(event_slug)
        for sess_dir in sorted([p for p in event_dir.iterdir() if p.is_dir()]):
            code = sess_dir.name
            rows.append({
                "Year": year,
                "EventName": event_name,
                "Country": "",
                "Location": "",
                "SessionCode": code,
                "Session": _SESSION_FRIENDLY.get(code, code),
                "StartUTC": pd.NaT,
                "StartLocal": pd.NaT
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    cat = pd.Categorical(df["SessionCode"], categories=_SESSION_ORDER, ordered=True)
    return df.assign(SessionOrder=cat).sort_values(["EventName", "SessionOrder"]).drop(columns=["SessionOrder"]).reset_index(drop=True)
