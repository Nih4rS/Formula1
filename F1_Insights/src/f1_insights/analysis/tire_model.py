from __future__ import annotations

import numpy as np
import pandas as pd


DEFAULT_FUEL_PENALTY_S_PER_KG = 0.03
DEFAULT_START_FUEL_KG = 100.0


def estimate_fuel_mass(lap_number: pd.Series, total_laps: int) -> pd.Series:
    burned_per_lap = DEFAULT_START_FUEL_KG / max(total_laps, 1)
    return np.maximum(DEFAULT_START_FUEL_KG - burned_per_lap * lap_number, 0)


def fuel_corrected_pace(laps_df: pd.DataFrame, lap_time_col: str = "lap_duration_s") -> pd.DataFrame:
    df = laps_df.copy()
    if lap_time_col not in df.columns:
        raise ValueError(f"Missing required column: {lap_time_col}")

    total_laps = int(df["lap_number"].max()) if "lap_number" in df.columns else len(df)
    fuel_mass = estimate_fuel_mass(df["lap_number"].fillna(1), total_laps=total_laps)
    df["fuel_mass_kg"] = fuel_mass
    df["fuel_effect_s"] = df["fuel_mass_kg"] * DEFAULT_FUEL_PENALTY_S_PER_KG
    df["fuel_corrected_lap_s"] = pd.to_numeric(df[lap_time_col], errors="coerce") - df["fuel_effect_s"]
    df["degradation_trend_s"] = df["fuel_corrected_lap_s"].rolling(window=5, min_periods=2).mean()
    return df
