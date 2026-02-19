from __future__ import annotations

import pandas as pd

from .schemas import DataSourceType, OPEN_SCHEMA_COLUMNS, USER_SCHEMA_COLUMNS


USER_SYNONYMS = {
    "distance": "lap_distance_m",
    "lap_distance": "lap_distance_m",
    "speed": "speed_kph",
    "throttle": "throttle_pct",
    "brake": "brake_pct",
    "driver": "driver_code",
    "lap": "lap_number",
}

OPEN_SYNONYMS = {
    "driver": "driver_number",
    "lap": "lap_number",
    "lap_duration": "lap_duration_s",
    "sector_1": "sector_1_s",
    "sector_2": "sector_2_s",
    "sector_3": "sector_3_s",
}


def _rename_with_synonyms(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    for col in df.columns:
        lowered = col.strip().lower()
        if lowered in mapping:
            rename_map[col] = mapping[lowered]
    return df.rename(columns=rename_map)


def normalize_user_telemetry(df: pd.DataFrame, session_id: str) -> pd.DataFrame:
    df = _rename_with_synonyms(df.copy(), USER_SYNONYMS)
    df["source_type"] = DataSourceType.USER_UPLOAD.value
    df["session_id"] = session_id

    for required in USER_SCHEMA_COLUMNS:
        if required not in df.columns:
            df[required] = None

    numeric_cols = ["lap_number", "lap_distance_m", "speed_kph", "throttle_pct", "brake_pct", "gear", "rpm"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df[USER_SCHEMA_COLUMNS]


def normalize_open_historical(df: pd.DataFrame) -> pd.DataFrame:
    df = _rename_with_synonyms(df.copy(), OPEN_SYNONYMS)
    df["source_type"] = DataSourceType.OPEN_HISTORICAL.value

    for required in OPEN_SCHEMA_COLUMNS:
        if required not in df.columns:
            df[required] = None

    numeric_cols = [
        "session_key",
        "driver_number",
        "lap_number",
        "lap_duration_s",
        "sector_1_s",
        "sector_2_s",
        "sector_3_s",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df[OPEN_SCHEMA_COLUMNS]
