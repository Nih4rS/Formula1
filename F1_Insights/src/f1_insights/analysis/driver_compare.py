from __future__ import annotations

import pandas as pd


def telemetry_bin_average(df: pd.DataFrame, bin_size_m: float = 50.0) -> pd.DataFrame:
    out = df.copy()
    out["bin_index"] = (out["lap_distance_m"] // bin_size_m).astype("Int64")
    grouped = (
        out.groupby(["driver_code", "lap_number", "bin_index"], dropna=True)
        .agg(
            speed_kph=("speed_kph", "mean"),
            throttle_pct=("throttle_pct", "mean"),
            brake_pct=("brake_pct", "mean"),
        )
        .reset_index()
    )
    return grouped


def compare_two_drivers(df: pd.DataFrame, driver_a: str, driver_b: str) -> pd.DataFrame:
    binned = telemetry_bin_average(df)
    a = binned[binned["driver_code"] == driver_a].rename(
        columns={
            "speed_kph": "speed_a",
            "throttle_pct": "throttle_a",
            "brake_pct": "brake_a",
        }
    )
    b = binned[binned["driver_code"] == driver_b].rename(
        columns={
            "speed_kph": "speed_b",
            "throttle_pct": "throttle_b",
            "brake_pct": "brake_b",
        }
    )

    merged = a.merge(b, on=["lap_number", "bin_index"], how="inner")
    merged["speed_delta_kph"] = merged["speed_a"] - merged["speed_b"]
    return merged
