from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from f1_insights.analysis.tire_model import fuel_corrected_pace
from f1_insights.data.ingestion import load_open_historical_laps

st.title("Open Historical Insights")
st.caption("Derived analytics from open historical session data")

session_key = st.number_input("OpenF1 session_key", min_value=1, value=9158, step=1)

@st.cache_data(show_spinner=False)
def cached_laps(key: int):
    return load_open_historical_laps(key)

if st.button("Load session laps"):
    with st.spinner("Fetching historical lap data..."):
        laps, errors = cached_laps(int(session_key))

    st.dataframe(laps.head(30), use_container_width=True)

    if errors:
        st.warning(f"Validation warnings: {len(errors)}")

    if "lap_duration_s" in laps.columns and laps["lap_duration_s"].notna().any():
        modeled = fuel_corrected_pace(laps)
        st.subheader("Fuel-corrected pace trend")
        fig = px.line(modeled, x="lap_number", y="fuel_corrected_lap_s", color="driver_number")
        st.plotly_chart(fig, use_container_width=True)

        trend_fig = px.line(modeled, x="lap_number", y="degradation_trend_s", color="driver_number")
        st.plotly_chart(trend_fig, use_container_width=True)
    else:
        st.info("No lap duration values returned for this session key.")
