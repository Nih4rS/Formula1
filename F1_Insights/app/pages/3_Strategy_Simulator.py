from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from f1_insights.simulation.strategy import run_monte_carlo_strategy, summarize_strategy

st.title("Strategy Simulator")
st.caption("Monte Carlo race-time simulation for pit window exploration")

left, right = st.columns(2)
with left:
    n_runs = st.slider("Simulation runs", min_value=200, max_value=10000, value=2000, step=200)
    laps = st.slider("Race laps", min_value=20, max_value=90, value=57, step=1)
    pit_lap = st.slider("Pit lap", min_value=2, max_value=89, value=22, step=1)
with right:
    base_lap_s = st.slider("Base lap time (s)", min_value=65.0, max_value=110.0, value=90.0, step=0.1)
    pit_loss_s = st.slider("Pit loss (s)", min_value=15.0, max_value=35.0, value=21.5, step=0.1)
    deg_per_lap_s = st.slider("Degradation per lap (s)", min_value=0.01, max_value=0.25, value=0.06, step=0.01)

if st.button("Run simulation"):
    results = run_monte_carlo_strategy(
        n_runs=n_runs,
        base_lap_s=base_lap_s,
        laps=laps,
        pit_lap=min(pit_lap, laps - 1),
        pit_loss_s=pit_loss_s,
        deg_per_lap_s=deg_per_lap_s,
    )
    summary = summarize_strategy(results)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mean", f"{summary['mean_s']:.2f}s")
    c2.metric("P10", f"{summary['p10_s']:.2f}s")
    c3.metric("P50", f"{summary['p50_s']:.2f}s")
    c4.metric("P90", f"{summary['p90_s']:.2f}s")

    hist = px.histogram(results, x="race_time_s", nbins=40, title="Race Time Distribution")
    st.plotly_chart(hist, use_container_width=True)
    st.dataframe(results.head(30), use_container_width=True)
