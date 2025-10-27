import plotly.graph_objects as go
from typing import List, Dict

def line(title: str, x: List[float], y: List[float], name: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
    fig.update_layout(title=title, xaxis_title="Distance (m)",
                      template="plotly_dark", height=380, margin=dict(l=40,r=20,b=40,t=50))
    return fig

def multi_line(title: str, traces: Dict[str, Dict[str, List[float]]]) -> go.Figure:
    fig = go.Figure()
    for name, data in traces.items():
        fig.add_trace(go.Scatter(x=data["x"], y=data["y"], mode="lines", name=name))
    fig.update_layout(title=title, xaxis_title="Distance (m)",
                      template="plotly_dark", height=360, legend=dict(orientation="h"),
                      margin=dict(l=40,r=20,b=40,t=50))
    return fig
