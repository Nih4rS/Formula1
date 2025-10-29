import streamlit as st
import numpy as np

from utils.data_loader import list_years, list_events, list_sessions, list_drivers, load_lap
from utils.lap_delta import lap_delta
from utils.plotting import line, multi_line
from utils.map_loader import load_map_data, build_track_figure

st.set_page_config(page_title="F1 Lap Explorer", layout="wide")

st.title("F1 Lap Explorer")
st.caption("Compare best laps, deltas, and speed traces. Data from FastF1-derived JSON in this repo.")

# Sidebar selectors
years = list_years()
if not years:
    st.error("No data found. Run the ETL to populate /data.")
    st.stop()

year = st.sidebar.selectbox("Year", years, index=len(years)-1)
events = list_events(year)
event = st.sidebar.selectbox("Grand Prix", events, index=0) if events else st.stop()
# ---- TRACK MAP SECTION ----
st.markdown("---")
st.header("Circuit Map")

map_data = load_map_data(year, event)
if not map_data:
    st.warning("No map data found for this Grand Prix. Run build_maps.py to generate it.")
else:
    fig_map = build_track_figure(map_data, event)
    st.plotly_chart(fig_map, use_container_width=True)

sessions = list_sessions(year, event)
session = st.sidebar.selectbox("Session", sessions, index=0) if sessions else st.stop()

drivers = list_drivers(year, event, session)
if len(drivers) < 2:
    st.warning("Need at least two drivers in data to compare")
    st.stop()

ref_driver = st.sidebar.selectbox("Reference", drivers, index=0)
cmp_choices = [d for d in drivers if d != ref_driver]
cmp_multi = st.sidebar.multiselect("Compare vs", cmp_choices, default=cmp_choices[:2])

# Load laps
ref = load_lap(year, event, session, ref_driver)

# charts
speed_traces = {ref_driver: {"x": ref["distance_m"], "y": ref["speed_kph"]}}

delta_traces = []
for drv in cmp_multi:
    try:
        cmp = load_lap(year, event, session, drv)
        dx, dy = lap_delta(ref["distance_m"], ref["cum_lap_time_s"], cmp["distance_m"], cmp["cum_lap_time_s"])
        delta_traces.append((f"{drv} vs {ref_driver}", dx, dy))
        speed_traces[drv] = {"x": cmp["distance_m"], "y": cmp["speed_kph"]}
    except Exception as e:
        st.warning(f"Failed to load {drv}: {e}")

col1, col2 = st.columns(2, gap="large")

with col1:
    if delta_traces:
        fig = multi_line("Lap Time Delta vs Distance (positive = slower than reference)",
                         {name: {"x": x, "y": y} for name, x, y in delta_traces})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pick at least one comparison driver")

with col2:
    fig2 = multi_line("Speed Trace (km/h)", speed_traces)
    st.plotly_chart(fig2, use_container_width=True)

# Advanced overlays
st.subheader("Throttle and Brake overlays")
tb_pick = st.multiselect("Choose drivers", [ref_driver] + cmp_choices, default=[ref_driver] + cmp_choices[:1])
t_traces, b_traces = {}, {}
for drv in tb_pick:
    try:
        lap = load_lap(year, event, session, drv)
        # Normalize to 0..100 for readability if None values present
        thr = [v*100 if isinstance(v, (int,float)) and v is not None else None for v in lap.get("throttle", [])]
        brk = [v*100 if isinstance(v, (int,float)) and v is not None else None for v in lap.get("brake", [])]
        t_traces[drv] = {"x": lap["distance_m"], "y": thr}
        b_traces[drv] = {"x": lap["distance_m"], "y": brk}
    except Exception as e:
        st.warning(f"{drv} overlay failed: {e}")

c1, c2 = st.columns(2, gap="large")
with c1:
    st.plotly_chart(multi_line("Throttle %", t_traces), use_container_width=True)
with c2:
    st.plotly_chart(multi_line("Brake %", b_traces), use_container_width=True)

st.markdown(
    "Tip: click legend labels to hide/show traces. Use the camera icon to download PNG."
)
