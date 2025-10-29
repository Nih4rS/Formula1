# utils/schedule.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Tuple, Optional

import pandas as pd
import fastf1

# Ensure FastF1 cache is on (same cache folder your ETL uses)
from pathlib import Path
CACHE = Path("fastf1_cache")
CACHE.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(CACHE)

_SESSION_ORDER = [
    "FP1", "FP2", "FP3", "SS", "SQ", "SPR", "Q", "R"
]
_SESSION_FRIENDLY = {
    "FP1": "Free Practice 1",
    "FP2": "Free Practice 2",
    "FP3": "Free Practice 3",
    "SS":  "Sprint Shootout",
    "SQ":  "Sprint Qualifying",
    "SPR": "Sprint",
    "Q":   "Qualifying",
    "R":   "Race"
}

def _localize(ts_utc: Optional[pd.Timestamp]) -> Optional[pd.Timestamp]:
    if ts_utc is None or pd.isna(ts_utc):
        return None
    if ts_utc.tzinfo is None:
        ts_utc = ts_utc.tz_localize("UTC")
    return ts_utc.tz_convert(None).to_pydatetime().astimezone()  # system local tz


def fetch_schedule(year: int) -> pd.DataFrame:
    """Return tidy schedule with one row per session and both UTC and Local times."""
    sched = fastf1.get_event_schedule(year, include_testing=False)

    # FastF1 keeps per-session UTC columns; collect them into long form
    rows = []
    for _, ev in sched.iterrows():
        event = str(ev["EventName"])
        gp_key = str(ev["EventName"])
        country = ev.get("Country", "")
        location = ev.get("Location", "")

        for code in ["FP1", "FP2", "FP3", "SS", "SQ", "SPR", "Q", "R"]:
            utc_col = f"{code}Date"
            if utc_col in ev and pd.notna(ev[utc_col]):
                ts_utc = pd.to_datetime(ev[utc_col], utc=True)
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
        return df

    # nice sorting
    cat = pd.Categorical(df["SessionCode"], categories=_SESSION_ORDER, ordered=True)
    df = df.assign(SessionOrder=cat).sort_values(["StartUTC", "EventName", "SessionOrder"]).reset_index(drop=True)
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
