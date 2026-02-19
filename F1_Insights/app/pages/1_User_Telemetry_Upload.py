from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from f1_insights.analysis.driver_compare import compare_two_drivers
from f1_insights.data.ingestion import load_uploaded_table
from f1_insights.legal.compliance import ATTESTATION_TEXT

st.title("User Telemetry Upload")
st.caption("Post-race deep dive using your own exported telemetry")

session_id = st.text_input("Session ID", value="user-session-001")
attested = st.checkbox(ATTESTATION_TEXT)
uploaded = st.file_uploader("Upload telemetry (CSV or Parquet)", type=["csv", "parquet"])

if uploaded and attested:
    df, errors = load_uploaded_table(uploaded, session_id=session_id)
    st.write("Normalized dataset preview")
    st.dataframe(df.head(20), use_container_width=True)

    if errors:
        st.warning(f"Validation warnings (showing up to 25): {len(errors)}")
        for err in errors[:10]:
            st.write(f"- {err}")
    else:
        st.success("Schema validation passed")

    valid_driver_values = [value for value in df["driver_code"].dropna().astype(str).unique().tolist() if value]
    if len(valid_driver_values) >= 2:
        d1, d2 = st.columns(2)
        with d1:
            driver_a = st.selectbox("Driver A", options=valid_driver_values, index=0)
        with d2:
            driver_b = st.selectbox("Driver B", options=valid_driver_values, index=1)

        if driver_a != driver_b:
            compared = compare_two_drivers(df, driver_a=driver_a, driver_b=driver_b)
            st.subheader("Binned speed delta")
            chart_df = compared[["lap_number", "bin_index", "speed_delta_kph"]].copy()
            fig = px.line(chart_df, x="bin_index", y="speed_delta_kph", color="lap_number")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(compared.head(30), use_container_width=True)
    else:
        st.info("Need at least two distinct driver codes for comparison.")

elif uploaded and not attested:
    st.error("Please confirm legal data attestation before analysis.")
else:
    st.info("Upload a file to begin.")
