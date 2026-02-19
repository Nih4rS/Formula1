from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from f1_insights.legal.compliance import COMPLIANCE_BULLETS, DEFAULT_POLICY

st.title("Compliance Guardrails")
st.caption("Operational boundaries for legal-safe, transformative analytics")

st.subheader("Current policy flags")
st.json(
    {
        "allow_live_timing_replication": DEFAULT_POLICY.allow_live_timing_replication,
        "allow_rebroadcast_stream": DEFAULT_POLICY.allow_rebroadcast_stream,
        "allow_direct_betting_feed": DEFAULT_POLICY.allow_direct_betting_feed,
        "require_user_data_attestation": DEFAULT_POLICY.require_user_data_attestation,
    }
)

st.subheader("App-level constraints")
for bullet in COMPLIANCE_BULLETS:
    st.write(f"- {bullet}")

st.warning(
    "This project is for analytics and research workflows. It is not legal advice. "
    "Confirm your own licensing and jurisdictional requirements before deployment."
)
