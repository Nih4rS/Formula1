# utils/map_loader.py
from __future__ import annotations

import json
import pathlib
from functools import lru_cache
from typing import Dict

import fastf1
import pandas as pd
import plotly.graph_objects as go

from utils.events import slug_to_event_name

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
CACHE = pathlib.Path("fastf1_cache")
CACHE.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(CACHE)

SESSION_TRY_ORDER = ["Q", "SQ", "SS", "FP2", "FP3", "FP1", "R"]


def load_map_data(year: str | int, event_slug: str) -> dict:
    """Load circuit assets; auto-build from FastF1 if files are missing."""
    base = DATA / str(year) / event_slug
    out = _read_map_dir(base)
    if "track_map" not in out:
        out.update(_auto_generate_map(year, event_slug))
    return out


def _read_map_dir(base: pathlib.Path) -> Dict[str, dict]:
    payload: Dict[str, dict] = {}
    for name in ("track_map", "corners", "sectors"):
        fp = base / f"{name}.json"
        if fp.exists():
            try:
                payload[name] = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
    return payload


def _auto_generate_map(year: int | str, event_slug: str) -> Dict[str, dict]:
    """Build map data via FastF1 and persist for reuse."""
    bundle = _fetch_map_bundle(int(year), event_slug)
    if not bundle:
        return {}
    base = DATA / str(year) / event_slug
    base.mkdir(parents=True, exist_ok=True)
    for name, content in bundle.items():
        (base / f"{name}.json").write_text(json.dumps(content), encoding="utf-8")
    return bundle


@lru_cache(maxsize=32)
def _fetch_map_bundle(year: int, event_slug: str) -> Dict[str, dict]:
    session = _load_any_session(year, event_slug)
    if session is None:
        return {}
    try:
        fastest = session.laps.pick_fastest()
        telemetry = fastest.get_telemetry()
    except Exception:
        return {}
    if telemetry is None or telemetry.empty or not {"X", "Y"}.issubset(telemetry.columns):
        return {}

    bundle: Dict[str, dict] = {
        "track_map": {"X": telemetry["X"].tolist(), "Y": telemetry["Y"].tolist()}
    }

    try:
        ci = session.get_circuit_info()
    except Exception:
        ci = None

    if ci is not None:
        corners_df = getattr(ci, "corners", None)
        if isinstance(corners_df, pd.DataFrame) and not corners_df.empty:
            bundle["corners"] = corners_df.to_dict(orient="records")
        sectors_df = getattr(ci, "sectors", None)
        if (
            isinstance(sectors_df, pd.DataFrame)
            and not sectors_df.empty
            and {"X", "Y"}.issubset(sectors_df.columns)
        ):
            bundle["sectors"] = sectors_df.to_dict(orient="records")

    return bundle


def _load_any_session(year: int, event_slug: str):
    """Return first session with telemetry available."""
    event_name = slug_to_event_name(event_slug)
    for code in SESSION_TRY_ORDER:
        try:
            session = fastf1.get_session(year, event_name, code)
            session.load(telemetry=True, laps=True, weather=False)
            return session
        except Exception:
            continue
    return None


def build_track_figure(map_data: dict, event_name: str, selected_turn: int | None = None) -> go.Figure:
    """Circuit layout with optional selected turn highlight."""
    fig = go.Figure()

    # Track polyline
    if "track_map" in map_data:
        X, Y = map_data["track_map"]["X"], map_data["track_map"]["Y"]
        fig.add_trace(go.Scatter(
            x=X, y=Y, mode="lines",
            line=dict(color="white", width=2),
            name="Track"
        ))

    # Optional colored sectors (if XY present)
    if "sectors" in map_data and isinstance(map_data["sectors"], list):
        colors = ["#e74c3c", "#f1c40f", "#2ecc71", "#3498db"]
        for i, s in enumerate(map_data["sectors"]):
            if isinstance(s, dict) and "X" in s and "Y" in s:
                fig.add_trace(go.Scatter(
                    x=s["X"], y=s["Y"], mode="lines",
                    line=dict(color=colors[i % len(colors)], width=4),
                    name=f"Sector {i+1}", opacity=0.35,
                    hoverinfo="skip", showlegend=False
                ))

    # Turn markers + labels
    if "corners" in map_data and isinstance(map_data["corners"], list):
        turns = map_data["corners"]
        xs = [t["X"] for t in turns]
        ys = [t["Y"] for t in turns]
        labels = [f"T{t['Number']}" for t in turns]
        nums = [t["Number"] for t in turns]

        # base points
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text",
            text=labels, textposition="top center",
            marker=dict(color="rgba(255,80,80,0.8)", size=8),
            hovertext=[t.get("Name", f"Turn {t['Number']}") for t in turns],
            name="Turns", customdata=nums
        ))

        # selected turn overlay
        if selected_turn is not None and selected_turn in nums:
            i = nums.index(selected_turn)
            fig.add_trace(go.Scatter(
                x=[xs[i]], y=[ys[i]], mode="markers+text",
                text=[labels[i]], textposition="top center",
                marker=dict(color="rgb(0,200,255)", size=14, line=dict(color="white", width=1.5)),
                name=f"Selected T{selected_turn}", customdata=[selected_turn],
                hovertext=[f"Selected T{selected_turn}"]
            ))

    fig.update_layout(
        title=f"{event_name.title().replace('-', ' ')} Circuit Layout",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        template="plotly_dark", height=600,
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(orientation="h", y=-0.08),
    )
    return fig
