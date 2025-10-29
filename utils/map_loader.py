# utils/map_loader.py
import json, pathlib
import plotly.graph_objects as go

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

def load_map_data(year: str, event: str):
    """Return dict with track, corners, sectors if available."""
    base = DATA / year / event
    result = {}
    for name in ["track_map", "corners", "sectors"]:
        fp = base / f"{name}.json"
        if fp.exists():
            result[name] = json.loads(fp.read_text(encoding="utf-8"))
    return result

def build_track_figure(map_data: dict, event_name: str) -> go.Figure:
    """Plotly figure for the circuit with colored sectors and corner labels."""
    fig = go.Figure()

    # --- main track line
    if "track_map" in map_data:
        X, Y = map_data["track_map"]["X"], map_data["track_map"]["Y"]
        fig.add_trace(go.Scatter(x=X, y=Y, mode="lines",
                                 line=dict(color="white", width=2),
                                 name="Track"))

    # --- color-coded sectors
    if "sectors" in map_data:
        colors = ["#e74c3c", "#f1c40f", "#2ecc71", "#3498db"]
        for i, s in enumerate(map_data["sectors"]):
            try:
                xs, ys = s["X"], s["Y"]
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, mode="lines",
                    line=dict(color=colors[i % len(colors)], width=4),
                    name=f"Sector {i+1}"
                ))
            except Exception:
                continue

    # --- turn markers
    if "corners" in map_data:
        turns = map_data["corners"]
        fig.add_trace(go.Scatter(
            x=[t["X"] for t in turns],
            y=[t["Y"] for t in turns],
            mode="markers+text",
            text=[f"T{t['Number']}" for t in turns],
            textposition="top center",
            marker=dict(color="red", size=8),
            hovertext=[t.get("Name", f"Turn {t['Number']}") for t in turns],
            name="Turns"
        ))

    fig.update_layout(
        title=f"{event_name.title().replace('-', ' ')} Circuit Layout",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        template="plotly_dark",
        height=600,
        margin=dict(l=10, r=10, t=60, b=10),
        legend=dict(orientation="h", y=-0.1)
    )
    return fig
