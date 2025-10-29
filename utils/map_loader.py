# utils/map_loader.py
from __future__ import annotations
import json, pathlib
import plotly.graph_objects as go

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


def load_map_data(year: str | int, event: str) -> dict:
    """Load prebuilt JSONs for a GP. Returns dict keys: track_map, corners, sectors (if found)."""
    base = DATA / str(year) / event
    out: dict = {}
    for name in ("track_map", "corners", "sectors"):
        fp = base / f"{name}.json"
        if fp.exists():
            out[name] = json.loads(fp.read_text(encoding="utf-8"))
    return out


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
