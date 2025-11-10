# models/position.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from joblib import dump, load

from features.extract import extract_session_features, build_training_frame

MODEL_DIR = Path("model_store")
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / "position_model.pkl"
META_PATH = MODEL_DIR / "position_model.meta.json"


def _xy(df: pd.DataFrame):
    feats = df[["Grid", "QPos"]].astype(float)
    # Simple normalization guard
    feats = feats.replace([np.inf, -np.inf], np.nan).fillna(40.0)
    y = df["TargetPos"].astype(float)
    return feats, y


def train_model(year_start: int, year_end: int) -> dict:
    """Train a very simple regressor predicting finish position.

    Saves artifact to MODEL_PATH and returns metrics/meta.
    """
    data = build_training_frame(year_start, year_end)
    if data.empty:
        raise RuntimeError("No training data could be built from FastF1 schedule.")

    X, y = _xy(data)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    mae = float(mean_absolute_error(yte, pred))

    dump(model, MODEL_PATH)
    meta = {
        "years": [year_start, year_end],
        "mae": mae,
        "n_samples": int(len(data)),
        "features": ["Grid", "QPos"],
        "target": "TargetPos",
    }
    META_PATH.write_text(json.dumps(meta, indent=2))
    return meta


def ensure_model(year_start: int, year_end: int) -> dict:
    if MODEL_PATH.exists() and META_PATH.exists():
        try:
            _ = load(MODEL_PATH)
            meta = json.loads(META_PATH.read_text())
            return meta
        except Exception:
            pass
    return train_model(year_start, year_end)


def predict_for_race(year: int, event_slug: str, year_start: Optional[int] = None, year_end: Optional[int] = None) -> pd.DataFrame:
    """Predict finishing positions for a given race using the trained model.

    If no model exists, it will train using given year range or fallback to
    (year-5 .. year-1).
    """
    if not MODEL_PATH.exists():
        ys = year_start if year_start is not None else max(year - 5, 2018)
        ye = year_end if year_end is not None else (year - 1)
        ensure_model(ys, ye)

    model = load(MODEL_PATH)
    pack = extract_session_features(year, event_slug, "R")
    df = pack.frame.copy()
    if df.empty:
        return pd.DataFrame()

    X, _ = _xy(df)
    pred = model.predict(X)
    out = df[["Driver", "Team", "Grid", "QPos"]].copy()
    out["PredictedPos"] = pred
    out = out.sort_values("PredictedPos").reset_index(drop=True)
    out["PredictedPos"] = out["PredictedPos"].round(2)
    return out
