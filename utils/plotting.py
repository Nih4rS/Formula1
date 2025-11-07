import plotly.graph_objects as go
from typing import Dict, List, Optional, Sequence, Tuple

def line(title: str, x: List[float], y: List[float], name: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
    fig.update_layout(title=title, xaxis_title="Distance (m)",
                      template="plotly_dark", height=380, margin=dict(l=40,r=20,b=40,t=50))
    return fig

def multi_line(
    title: str,
    traces: Dict[str, Dict[str, List[float]]],
    *,
    xaxis_title: str = "Distance (m)",
    yaxis_title: Optional[str] = None,
    height: int = 360,
    xaxis_range: Optional[Tuple[float, float]] = None,
    shapes: Optional[Sequence[dict]] = None,
) -> go.Figure:
    fig = go.Figure()
    for name, data in traces.items():
        fig.add_trace(go.Scatter(x=data["x"], y=data["y"], mode="lines", name=name))
    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        template="plotly_dark",
        height=height,
        legend=dict(orientation="h"),
        margin=dict(l=40, r=20, b=40, t=50),
        shapes=list(shapes) if shapes else None,
    )
    if xaxis_range:
        fig.update_xaxes(range=list(xaxis_range))
    return fig
