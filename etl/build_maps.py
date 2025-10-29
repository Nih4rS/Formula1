# etl/build_maps.py
from __future__ import annotations
import sys, json, pathlib
from typing import Optional
import fastf1
import pandas as pd

SESSION_TRY_ORDER = ["Q", "SQ", "SS", "FP2", "FP3", "FP1", "R"]

def _load_any_session(year: int, event: str):
    """Return the first session that loads with laps+telemetry."""
    for code in SESSION_TRY_ORDER:
        try:
            s = fastf1.get_session(year, event, code)
            s.load(telemetry=True, laps=True, weather=False)
            return s, code
        except Exception:
            continue
    return None, None

# Enable cache
CACHE = pathlib.Path("fastf1_cache")
CACHE.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(CACHE)

DATA = pathlib.Path("data")


def _slug(event: str) -> str:
    return event.lower().replace(" ", "-")


def _to_records_safe(df: Optional[pd.DataFrame]) -> Optional[list]:
    try:
        if df is None: 
            return None
        if hasattr(df, "empty") and df.empty:
            return None
        return df.to_dict(orient="records")
    except Exception:
        return None


def export_track(year: int, event: str) -> bool:
    """
    Writes:
      data/<year>/<event-slug>/track_map.json
      data/<year>/<event-slug>/corners.json (if available)
      data/<year>/<event-slug>/sectors.json (if available and has XY)
    """
    # Load a qualifying session for robust fastest lap telemetry
    try:
        s, used = _load_any_session(year, event)
        if s is None:
            print(f"⚠️  skip: {year} {event} — no session with telemetry available")
            return False

    except Exception as e:
        print(f"⚠️  skip: {year} {event} — cannot load session ({e})")
        return False

    out_dir = DATA / str(year) / _slug(event)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Track outline from overall fastest lap telemetry
    try:
        fastest = s.laps.pick_fastest()
    except Exception:
        fastest = None

    if fastest is None or (isinstance(fastest, pd.Series) and fastest.empty):
        print(f"⚠️  skip: {year} {event} — no fastest lap available")
        return False

    try:
        tel = fastest.get_telemetry()
        if not {"X", "Y"}.issubset(tel.columns):
            print(f"⚠️  skip: {year} {event} — telemetry has no X/Y")
            return False
        coords = {"X": tel["X"].tolist(), "Y": tel["Y"].tolist()}
        (out_dir / "track_map.json").write_text(json.dumps(coords), encoding="utf-8")
    except Exception as e:
        print(f"⚠️  skip: {year} {event} — cannot extract XY ({e})")
        return False

    # CircuitInfo is an object with .corners and .sectors attributes in FastF1
    # These are DataFrames or None depending on availability
    try:
        ci = s.get_circuit_info()
    except Exception:
        ci = None

    if ci is not None:
        # corners
        try:
            corners_rec = _to_records_safe(getattr(ci, "corners", None))
            if corners_rec:
                (out_dir / "corners.json").write_text(json.dumps(corners_rec, indent=2), encoding="utf-8")
        except Exception:
            pass

        # sectors (only write if XY present)
        try:
            sectors_df = getattr(ci, "sectors", None)
            if sectors_df is not None and not sectors_df.empty and {"X", "Y"}.issubset(sectors_df.columns):
                sectors_rec = sectors_df.to_dict(orient="records")
                (out_dir / "sectors.json").write_text(json.dumps(sectors_rec, indent=2), encoding="utf-8")
        except Exception:
            pass

    print(f"✅ saved track map for {year} {event}")
    return True


def build_all_tracks(year: int) -> None:
    sched = fastf1.get_event_schedule(year, include_testing=False)
    for _, row in sched.iterrows():
        ev = str(row["EventName"])
        try:
            export_track(year, ev)
        except Exception as e:
            print(f"⚠️  failed: {year} {ev} {e}")


if __name__ == "__main__":
    # CLI: python etl/build_maps.py <year> [<Event Name>]
    if len(sys.argv) < 2:
        print("Usage: python etl/build_maps.py <year> [<Event Name>]")
        sys.exit(1)
    yr = int(sys.argv[1])
    if len(sys.argv) == 2:
        build_all_tracks(yr)
    else:
        export_track(yr, sys.argv[2])
