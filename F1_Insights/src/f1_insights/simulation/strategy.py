from __future__ import annotations

import numpy as np
import pandas as pd


def run_monte_carlo_strategy(
    n_runs: int,
    base_lap_s: float,
    laps: int,
    pit_lap: int,
    pit_loss_s: float,
    deg_per_lap_s: float,
    noise_std_s: float = 0.35,
) -> pd.DataFrame:
    rows = []
    rng = np.random.default_rng(42)

    for run_id in range(n_runs):
        total = 0.0
        tire_age = 0
        for lap in range(1, laps + 1):
            if lap == pit_lap:
                total += pit_loss_s
                tire_age = 0

            lap_time = base_lap_s + deg_per_lap_s * tire_age + rng.normal(0, noise_std_s)
            total += lap_time
            tire_age += 1

        rows.append({"run_id": run_id, "race_time_s": total})

    frame = pd.DataFrame(rows)
    frame["race_time_s"] = frame["race_time_s"].round(3)
    return frame


def summarize_strategy(df: pd.DataFrame) -> dict[str, float]:
    return {
        "mean_s": float(df["race_time_s"].mean()),
        "p10_s": float(df["race_time_s"].quantile(0.10)),
        "p50_s": float(df["race_time_s"].quantile(0.50)),
        "p90_s": float(df["race_time_s"].quantile(0.90)),
    }
