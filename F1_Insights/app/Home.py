from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from f1_insights.legal.compliance import COMPLIANCE_BULLETS

st.set_page_config(page_title="F1 Insights", page_icon="🏎️", layout="wide")

st.title("F1 Insights: Transformative Analytics Workbench")
st.caption("Community-led post-race analysis and strategy simulation")

st.info(
    "This app is designed for derived analytics, not live timing replication. "
    "Use legally obtained user exports or open historical data only."
)

st.subheader("Modes")
col1, col2 = st.columns(2)
with col1:
    st.markdown("### User Telemetry Upload")
    st.write("Upload your own legally obtained telemetry export (CSV/Parquet).")
with col2:
    st.markdown("### Open Historical Insights")
    st.write("Analyze open/public historical lap data and run strategy simulations.")

st.subheader("Compliance Principles")
for bullet in COMPLIANCE_BULLETS:
    st.write(f"- {bullet}")

st.success("Next: Use the pages in the left sidebar to start analysis.")
