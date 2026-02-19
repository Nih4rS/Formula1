from __future__ import annotations

from io import BytesIO

import pandas as pd
import requests

from .normalization import normalize_open_historical, normalize_user_telemetry
from .schemas import validate_open_historical, validate_user_telemetry


OPENF1_BASE_URL = "https://api.openf1.org/v1"


def load_uploaded_table(uploaded_file, session_id: str) -> tuple[pd.DataFrame, list[str]]:
    suffix = uploaded_file.name.split(".")[-1].lower()
    raw_bytes = uploaded_file.getvalue()

    if suffix == "csv":
        raw_df = pd.read_csv(BytesIO(raw_bytes))
    elif suffix == "parquet":
        raw_df = pd.read_parquet(BytesIO(raw_bytes))
    else:
        raise ValueError("Only CSV or Parquet uploads are supported.")

    normalized = normalize_user_telemetry(raw_df, session_id=session_id)
    result = validate_user_telemetry(normalized)
    return normalized, result.errors


def fetch_openf1(endpoint: str, params: dict[str, str | int]) -> pd.DataFrame:
    url = f"{OPENF1_BASE_URL}/{endpoint.strip('/')}"
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return pd.DataFrame(payload)


def load_open_historical_laps(session_key: int) -> tuple[pd.DataFrame, list[str]]:
    raw_df = fetch_openf1("laps", {"session_key": session_key})
    normalized = normalize_open_historical(raw_df)
    result = validate_open_historical(normalized)
    return normalized, result.errors
