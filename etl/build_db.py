from __future__ import annotations
import json
from pathlib import Path
from typing import Iterable, Tuple
import sys

import duckdb  # type: ignore
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.events import slug_to_event_name, event_name_to_slug
from utils.schedule import fetch_schedule
DATA_ROOT = ROOT / "data"
DB_PATH = DATA_ROOT / "f1.duckdb"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS driver_sessions (
  year INTEGER,
  event_slug TEXT,
  event_name TEXT,
  session_code TEXT,
  driver TEXT,
  team TEXT,
  has_bestlap BOOLEAN
);

CREATE TABLE IF NOT EXISTS schedule (
  year INTEGER,
  event_slug TEXT,
  event_name TEXT,
  session_code TEXT,
  session TEXT,
  start_utc TIMESTAMP,
  start_local TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bestlap_metrics (
    year INTEGER,
    event_slug TEXT,
    event_name TEXT,
    session_code TEXT,
    driver TEXT,
    lap_time_s DOUBLE,
    distance_m DOUBLE,
    samples INTEGER,
    speed_min_kph DOUBLE,
    speed_avg_kph DOUBLE,
    speed_max_kph DOUBLE,
    throttle_mean_pct DOUBLE,
    brake_mean_pct DOUBLE,
    has_throttle BOOLEAN,
    has_brake BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_ds_y ON driver_sessions(year);
CREATE INDEX IF NOT EXISTS idx_ds_ye ON driver_sessions(year, event_slug);
CREATE INDEX IF NOT EXISTS idx_ds_yes ON driver_sessions(year, event_slug, session_code);
CREATE INDEX IF NOT EXISTS idx_ds_yesd ON driver_sessions(year, event_slug, session_code, driver);

CREATE INDEX IF NOT EXISTS idx_sched_y ON schedule(year);
CREATE INDEX IF NOT EXISTS idx_sched_ye ON schedule(year, event_slug);

CREATE INDEX IF NOT EXISTS idx_bl_y ON bestlap_metrics(year);
CREATE INDEX IF NOT EXISTS idx_bl_yesd ON bestlap_metrics(year, event_slug, session_code, driver);
"""


def _iter_sessions() -> Iterable[Tuple[int, str, str]]:
    if not DATA_ROOT.exists():
        return []
    for year_dir in sorted([p for p in DATA_ROOT.iterdir() if p.is_dir() and p.name.isdigit()]):
        year = int(year_dir.name)
        for event_dir in sorted([p for p in year_dir.iterdir() if p.is_dir()]):
            event_slug = event_dir.name
            for sess_dir in sorted([p for p in event_dir.iterdir() if p.is_dir()]):
                session_code = sess_dir.name
                yield year, event_slug, session_code


def _read_drivers_json(sess_dir: Path) -> dict:
    fp = sess_dir / "drivers.json"
    if fp.exists():
        try:
            return json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def build(reset: bool = True) -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    try:
        # light tuning: use available CPU threads
        try:
            import os
            nthreads = max(1, int(os.cpu_count() or 1))
            con.execute(f"PRAGMA threads = {nthreads};")
        except Exception:
            pass
        if reset:
            con.execute("DROP TABLE IF EXISTS driver_sessions;")
            con.execute("DROP TABLE IF EXISTS schedule;")
            con.execute("DROP TABLE IF EXISTS bestlap_metrics;")
        con.execute(SCHEMA_SQL)

        # Build driver_sessions
        rows = []
        for year, event_slug, session_code in _iter_sessions():
            event_name = slug_to_event_name(event_slug)
            sess_dir = DATA_ROOT / str(year) / event_slug / session_code
            drv_meta = _read_drivers_json(sess_dir)
            drivers = set()
            for f in sess_dir.glob("*_bestlap.json"):
                stem = f.stem
                if stem.endswith("_bestlap"):
                    drivers.add(stem[:-8])
            if not drivers and not drv_meta:
                # still write a row to mark session existence
                rows.append((year, event_slug, event_name, session_code, None, None, False))
            else:
                for d in (drivers or drv_meta.keys()):
                    meta = drv_meta.get(d, {}) if isinstance(drv_meta, dict) else {}
                    team = meta.get("Team") or meta.get("team") or None
                    has_bestlap = (sess_dir / f"{d}_bestlap.json").exists()
                    rows.append((year, event_slug, event_name, session_code, d, team, bool(has_bestlap)))
        if rows:
            df = pd.DataFrame(rows, columns=[
                "year", "event_slug", "event_name", "session_code", "driver", "team", "has_bestlap"
            ])
            con.register("df_driver_sessions", df)
            con.execute("INSERT INTO driver_sessions SELECT * FROM df_driver_sessions;")

        # Build bestlap_metrics
        metr_rows = []
        for year, event_slug, session_code in _iter_sessions():
            sess_dir = DATA_ROOT / str(year) / event_slug / session_code
            for f in sess_dir.glob("*_bestlap.json"):
                driver = f.stem[:-8] if f.stem.endswith("_bestlap") else f.stem
                try:
                    blob = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    continue
                # expected arrays
                dist = blob.get("distance_m") or []
                tcum = blob.get("cum_lap_time_s") or []
                spd = blob.get("speed_kph") or []
                thr = blob.get("throttle") if isinstance(blob.get("throttle"), list) else None
                brk = blob.get("brake") if isinstance(blob.get("brake"), list) else None
                try:
                    import numpy as np
                    t_arr = np.asarray(tcum, float)
                    s_arr = np.asarray(spd, float)
                    n = int(len(s_arr))
                    lap_time_s = float(np.nanmax(t_arr)) if n else None
                    dist_m = float(np.nanmax(np.asarray(dist, float))) if len(dist) else None
                    s_min = float(np.nanmin(s_arr)) if n else None
                    s_max = float(np.nanmax(s_arr)) if n else None
                    s_avg = float(np.nanmean(s_arr)) if n else None
                    thr_mean = None
                    brk_mean = None
                    has_thr = False
                    has_brk = False
                    if isinstance(thr, list) and thr:
                        tv = np.asarray(thr, float)
                        if np.nanmax(tv) <= 1.0:
                            tv = tv * 100.0
                        thr_mean = float(np.nanmean(tv))
                        has_thr = True
                    if isinstance(brk, list) and brk:
                        bv = np.asarray(brk, float)
                        if np.nanmax(bv) <= 1.0:
                            bv = bv * 100.0
                        brk_mean = float(np.nanmean(bv))
                        has_brk = True
                except Exception:
                    continue
                metr_rows.append((
                    year, event_slug, slug_to_event_name(event_slug), session_code, driver,
                    lap_time_s, dist_m, n, s_min, s_avg, s_max, thr_mean, brk_mean, has_thr, has_brk
                ))
        if metr_rows:
            dfm = pd.DataFrame(metr_rows, columns=[
                "year", "event_slug", "event_name", "session_code", "driver",
                "lap_time_s", "distance_m", "samples", "speed_min_kph", "speed_avg_kph", "speed_max_kph",
                "throttle_mean_pct", "brake_mean_pct", "has_throttle", "has_brake"
            ])
            con.register("df_bestlap_metrics", dfm)
            con.execute("INSERT INTO bestlap_metrics SELECT * FROM df_bestlap_metrics;")

        # Build schedule table from FastF1
        years = sorted({y for y, _, _ in _iter_sessions()})
        sched_rows = []
        for y in years:
            try:
                sched = fetch_schedule(int(y))
            except Exception:
                sched = pd.DataFrame()
            if not sched.empty:
                for _, r in sched.iterrows():
                    event_name = str(r.get("EventName", ""))
                    # use centralized slugging to stay consistent with filesystem/UI
                    event_slug = event_name_to_slug(event_name)
                    sched_rows.append((
                        int(y), event_slug, event_name,
                        r.get("SessionCode"), r.get("Session"),
                        pd.to_datetime(r.get("StartUTC"), utc=True).to_pydatetime() if pd.notna(r.get("StartUTC")) else None,
                        pd.to_datetime(r.get("StartLocal"), errors="coerce").to_pydatetime() if pd.notna(r.get("StartLocal")) else None,
                    ))
        if sched_rows:
            df_s = pd.DataFrame(sched_rows, columns=[
                "year", "event_slug", "event_name", "session_code", "session", "start_utc", "start_local"
            ])
            con.register("df_schedule", df_s)
            con.execute("INSERT INTO schedule SELECT * FROM df_schedule;")
    finally:
        con.close()
    return DB_PATH


if __name__ == "__main__":
    p = build(reset=True)
    print(f"Built DB at {p}")
