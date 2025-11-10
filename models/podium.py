# models/podium.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from joblib import dump, load

from features.extract import build_training_frame

MODEL_DIR = Path("model_store")
MODEL_DIR.mkdir(exist_ok=True)
MODEL_PATH = MODEL_DIR / "podium_model.pkl"
META_PATH = MODEL_DIR / "podium_model.meta.json"


def _xy(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    X = df[["Grid", "QPos"]].astype(float).replace([np.inf, -np.inf], np.nan).fillna(40.0)
    y = (df["TargetPos"] <= 3).astype(int)
    return X, y


def train_model(year_start: int, year_end: int) -> dict:
    data = build_training_frame(year_start, year_end)
    if data.empty:
        raise RuntimeError("No training data could be built.")
    X, y = _xy(data)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    clf = LogisticRegression(max_iter=2000)
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xte)
    acc = float(accuracy_score(yte, pred))
    pr, rc, f1, _ = precision_recall_fscore_support(yte, pred, average="binary", zero_division=0)

    dump(clf, MODEL_PATH)
    meta = {
        "years": [year_start, year_end],
        "accuracy": acc,
        "precision": float(pr),
        "recall": float(rc),
        "f1": float(f1),
        "n_samples": int(len(data)),
        "features": ["Grid", "QPos"],
        "target": "Podium (Top 3)",
    }
    META_PATH.write_text(json.dumps(meta, indent=2))
    return meta


def ensure_model(year_start: int, year_end: int) -> dict:
    if MODEL_PATH.exists() and META_PATH.exists():
        try:
            _ = load(MODEL_PATH)
            return json.loads(META_PATH.read_text())
        except Exception:
            pass
    return train_model(year_start, year_end)


def predict_proba_for_race(year: int, event_slug: str) -> pd.DataFrame:
    from features.extract import extract_session_features
    if not MODEL_PATH.exists():
        raise RuntimeError("Model not found; run train_model or ensure_model first.")
    clf = load(MODEL_PATH)
    pack = extract_session_features(year, event_slug, "R")
    df = pack.frame.copy()
    if df.empty:
        return pd.DataFrame()
    X, _ = _xy(df)
    proba = clf.predict_proba(X)[:, 1]
    out = df[["Driver", "Team", "Grid", "QPos"]].copy()
    out["PodiumProb"] = proba
    out = out.sort_values("PodiumProb", ascending=False).reset_index(drop=True)
    out["PodiumProb"] = (out["PodiumProb"] * 100).round(1)
    return out
