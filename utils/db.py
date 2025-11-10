from __future__ import annotations
from pathlib import Path
from typing import List, Optional
import duckdb  # type: ignore
import pandas as pd

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DATA_ROOT / "f1.duckdb"

_connection = None

def get_con():
    global _connection
    if _connection is None:
        if not DB_PATH.exists():
            raise FileNotFoundError("Database not built. Run etl/build_db.py")
        _connection = duckdb.connect(str(DB_PATH))
    return _connection


def list_years_db() -> List[str]:
    con = get_con()
    df = con.execute("SELECT DISTINCT year FROM driver_sessions ORDER BY year").fetchdf()
    return [str(y) for y in df["year"].tolist()]


def list_events_db(year: str | int) -> List[str]:
    con = get_con()
    df = con.execute("SELECT DISTINCT event_slug FROM driver_sessions WHERE year = ? ORDER BY event_slug", [int(year)]).fetchdf()
    return df["event_slug"].tolist()


def list_sessions_db(year: str | int, event_slug: str) -> List[str]:
    con = get_con()
    df = con.execute("SELECT DISTINCT session_code FROM driver_sessions WHERE year = ? AND event_slug = ? ORDER BY session_code", [int(year), event_slug]).fetchdf()
    return df["session_code"].tolist()


def list_drivers_db(year: str | int, event_slug: str, session_code: str) -> List[str]:
    con = get_con()
    df = con.execute("SELECT driver FROM driver_sessions WHERE year = ? AND event_slug = ? AND session_code = ? AND driver IS NOT NULL AND has_bestlap = TRUE ORDER BY driver", [int(year), event_slug, session_code]).fetchdf()
    return df["driver"].tolist()


def close():
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def get_bestlap_metrics(year: int | str, event_slug: Optional[str] = None, session_code: Optional[str] = None) -> pd.DataFrame:
    """Return best-lap summary metrics for the provided filters.

    If event_slug or session_code are None, they are not filtered.
    """
    con = get_con()
    sql = "SELECT * FROM bestlap_metrics WHERE year = ?"
    params: list = [int(year)]
    if event_slug:
        sql += " AND event_slug = ?"
        params.append(event_slug)
    if session_code:
        sql += " AND session_code = ?"
        params.append(session_code)
    sql += " ORDER BY event_slug, session_code, driver"
    return con.execute(sql, params).fetchdf()
