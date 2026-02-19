from __future__ import annotations

from enum import Enum
from typing import Iterable

import pandas as pd
from pydantic import BaseModel, Field, ValidationError


class DataSourceType(str, Enum):
    USER_UPLOAD = "user_upload"
    OPEN_HISTORICAL = "open_historical"


class TelemetryRecord(BaseModel):
    source_type: DataSourceType = Field(default=DataSourceType.USER_UPLOAD)
    session_id: str
    driver_code: str
    lap_number: int
    lap_distance_m: float
    speed_kph: float
    throttle_pct: float
    brake_pct: float
    gear: int | None = None
    rpm: float | None = None
    timestamp_utc: str | None = None


class HistoricalLapRecord(BaseModel):
    source_type: DataSourceType = Field(default=DataSourceType.OPEN_HISTORICAL)
    session_key: int
    driver_number: int
    lap_number: int
    lap_duration_s: float | None = None
    sector_1_s: float | None = None
    sector_2_s: float | None = None
    sector_3_s: float | None = None
    compound: str | None = None


USER_SCHEMA_COLUMNS = [
    "source_type",
    "session_id",
    "driver_code",
    "lap_number",
    "lap_distance_m",
    "speed_kph",
    "throttle_pct",
    "brake_pct",
    "gear",
    "rpm",
    "timestamp_utc",
]

OPEN_SCHEMA_COLUMNS = [
    "source_type",
    "session_key",
    "driver_number",
    "lap_number",
    "lap_duration_s",
    "sector_1_s",
    "sector_2_s",
    "sector_3_s",
    "compound",
]


class SchemaValidationResult(BaseModel):
    valid_rows: int
    invalid_rows: int
    errors: list[str]


def _validate_rows(records: Iterable[dict], model: type[BaseModel]) -> SchemaValidationResult:
    valid_rows = 0
    invalid_rows = 0
    errors: list[str] = []

    for idx, row in enumerate(records):
        try:
            model.model_validate(row)
            valid_rows += 1
        except ValidationError as err:
            invalid_rows += 1
            errors.append(f"row={idx}: {err.errors()[0]['msg']}")

    return SchemaValidationResult(valid_rows=valid_rows, invalid_rows=invalid_rows, errors=errors[:25])


def validate_user_telemetry(df: pd.DataFrame) -> SchemaValidationResult:
    return _validate_rows(df.to_dict(orient="records"), TelemetryRecord)


def validate_open_historical(df: pd.DataFrame) -> SchemaValidationResult:
    return _validate_rows(df.to_dict(orient="records"), HistoricalLapRecord)
