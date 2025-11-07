# streamlit_app.py
from __future__ import annotations
import json, pathlib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_plotly_events import plotly_events

# --- project utils
from utils.data_loader import list_years, list_events, list_sessions, list_drivers, load_lap
from utils.lap_delta import lap_delta
from utils.plotting import multi_line
from utils.map_loader import load_map_data, build_track_figure
from utils.schedule import fetch_schedule, next_session, countdown_str

# ---------------------------
# Page setup
# ---------------------------
st.set_page_config(page_title="F1 Lap Explorer", layout="wide")
st.title("F1 Lap Explorer")
st.caption("Compare best laps, speed traces, and turn-level telemetry with FastF1-derived data.")

# Sticky defaults
st.session_state.setdefault("year", None)
st.session_state.setdefault("event", None)
st.session_state.setdefault("session", None)
st.session_state.setdefault("ref", None)
st.session_state.setdefault("compares", [])
st.session_state.setdefault("selected_turn", None)

# ======================================================
# TABS
# ======================================================
tab_analysis, tab_schedule = st.tabs(["🔍 Analysis", "🗓️ Schedule"])

# ======================================================
# ===============  🗓️  SCHEDULE TAB  ====================
# ======================================================
with tab_schedule:
    st.subheader("Season Schedule")

    years_all = list_years() or list(range(2014, 2025 + 1))
    if st.session_state["year"] is None:
        st.session_state["year"] = years_all[-1]

    sched_year = st.selectbox("Year", years_all, index=years_all.index(st.session_state["year"]), key="sched_year")

    df_sched = fetch_schedule(int(sched_year))
    if df_sched.empty:
        st.info("No schedule data available yet for this year.")
    else:
        ns = next_session(df_sched)
        if ns is not None:
            cols = st.columns([1, 2, 2, 2, 2])
            with cols[0]:
                st.metric("Next", ns['EventName'], help=ns['Session'])
            with cols[1]:
                st.metric("Local time", ns['StartLocal'].strftime("%a %d %b %H:%M"))
            with cols[2]:
                st.metric("UTC", ns['StartUTC'].strftime("%a %d %b %H:%M"))
            with cols[3]:
                st.metric("Session", ns['Session'])
            with cols[4]:
                st.metric("Countdown", countdown_str(ns['StartUTC']))

        st.markdown("### Full Schedule")
        show_local = st.toggle("Show local time", value=True)
        dfv = df_sched.copy()
        dfv["Local"] = dfv["StartLocal"].dt.strftime("%a %d %b %H:%M")
        dfv["UTC"] = pd.to_datetime(dfv["StartUTC"]).dt.strftime("%a %d %b %H:%M")
        st.dataframe(dfv[["EventName", "Session", "Local" if show_local else "UTC"]],
                     use_container_width=True, height=420)

        st.divider()
        st.markdown("#### Jump to Analysis")

        evs = sorted(df_sched["EventName"].unique().tolist())
        choose_event = st.selectbox("Grand Prix", evs,
                                    index=evs.index(ns["EventName"]) if ns is not None else 0,
                                    key="sched_jump_event")

        gp_sessions = df_sched[df_sched["EventName"] == choose_event].sort_values("StartUTC")
        sess_codes = gp_sessions["SessionCode"].tolist()
        default_code = "R" if "R" in sess_codes else ("Q" if "Q" in sess_codes else sess_codes[0])
        choose_session = st.selectbox(
            "Session",
            [f"{row.Session} ({row.SessionCode})" for _, row in gp_sessions.iterrows()],
            index=sess_codes.index(default_code) if default_code in sess_codes else 0,
            key="sched_jump_session"
        )

        # --- FIXED BUTTON ---
        if st.button("Go to Analysis"):
            lbl = st.session_state["sched_jump_session"]
            code = lbl.split("(")[-1].rstrip(")")
            st.session_state["year"] = int(sched_year)
            st.session_state["event"] = choose_event
            st.session_state["session"] = code
            st.session_state["selected_turn"] = None
            st.experimental_rerun()

# ======================================================
# ===============  🔍 ANALYSIS TAB  =====================
# ======================================================
with tab_analysis:

    # --- Sidebar selectors ---
    years = list_years()
    if not years:
        st.error("No data found. Run ETL to populate /data.")
        st.stop()

    if st.session_state["year"] is None:
        st.session_state["year"] = years[-1]

    year = st.sidebar.selectbox("Year", years,
                                index=years.index(st.session_state["year"]), key="year")

    events = list_events(year)
    if not events:
        st.error("No Grands Prix found for this year.")
        st.stop()

    default_event = st.session_state["event"] if st.session_state["event"] in events else events[0]
    event = st.sidebar.selectbox("Grand Prix", events, index=events.index(default_event), key="event")

    sessions = list_sessions(year, event)
    if not sessions:
        st.warning("No sessions found for this event in /data. Run ETL or pick another GP.")
        st.stop()

    default_session = st.session_state["session"] if st.session_state["session"] in sessions else sessions[0]
    session = st.sidebar.selectbox("Session", sessions, index=sessions.index(default_session), key="session")

    drivers = list_drivers(year, event, session)
    if len(drivers) < 2:
        st.warning("Not enough driver data available for this session.")
        st.stop()

    default_ref = st.session_state["ref"] if st.session_state["ref"] in drivers else drivers[0]
    ref_driver = st.sidebar.selectbox("Reference", drivers, index=drivers.index(default_ref), key="ref")

    cmp_choices = [d for d in drivers if d != ref_driver]
    prev_compares = [c for c in st.session_state.get("compares", []) if c in cmp_choices]
    cmp_multi = st.sidebar.multiselect("Compare vs", cmp_choices,
                                       default=(prev_compares if prev_compares else cmp_choices[:2]),
                                       key="compares")

    # reset selected turn if event changed
    st.session_state["selected_turn"] = (
        st.session_state["selected_turn"] if st.session_state.get("_last_event") == event else None
    )
    st.session_state["_last_event"] = event

    # ---------------- Circuit Map ----------------
    st.markdown("---")
    st.header("Circuit Map")

    map_data = load_map_data(year, event)
    if not map_data:
        st.warning("No map data found. Run: `python etl/build_maps.py <year>`.")
        fig_map = None
        clicked = []
    else:
        fig_map = build_track_figure(map_data, event, selected_turn=st.session_state["selected_turn"])
        clicked = plotly_events(
            fig_map, click_event=True, hover_event=False, select_event=False,
            key="map_click", override_height=600, override_width="100%"
        )

    corners = map_data.get("corners", []) if map_data else []
    if clicked:
        pt = clicked[0]
        turn_num = pt.get("customdata")
        if turn_num is None and "pointIndex" in pt and corners:
            idx = int(pt["pointIndex"])
            if 0 <= idx < len(corners):
                turn_num = corners[idx]["Number"]
        if isinstance(turn_num, (int, np.integer)):
            st.session_state["selected_turn"] = int(turn_num)

    if fig_map is not None:
        fig_map = build_track_figure(map_data, event, selected_turn=st.session_state["selected_turn"])
        st.plotly_chart(fig_map, use_container_width=True)

    # ---------------- Lap Charts ----------------
    ref = load_lap(year, event, session, ref_driver)
    speed_traces = {ref_driver: {"x": ref["distance_m"], "y": ref["speed_kph"]}}
    delta_traces = []
    for drv in cmp_multi:
        try:
            cmp_lap = load_lap(year, event, session, drv)
            dx, dy = lap_delta(ref["distance_m"], ref["cum_lap_time_s"],
                               cmp_lap["distance_m"], cmp_lap["cum_lap_time_s"])
            delta_traces.append((f"{drv} vs {ref_driver}", dx, dy))
            speed_traces[drv] = {"x": cmp_lap["distance_m"], "y": cmp_lap["speed_kph"]}
        except Exception as e:
            st.warning(f"Failed to load {drv}: {e}")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        if delta_traces:
            fig = multi_line("Lap Time Delta vs Distance (positive = slower than reference)",
                             {name: {"x": x, "y": y} for name, x, y in delta_traces})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pick at least one comparison driver.")
    with c2:
        st.plotly_chart(multi_line("Speed Trace (km/h)", speed_traces), use_container_width=True)

    # ---------------- Throttle / Brake overlays ----------------
    st.subheader("Throttle and Brake overlays")
    tb_pick = st.multiselect("Choose drivers", [ref_driver] + cmp_choices,
                             default=[ref_driver] + cmp_choices[:1], key="tb_drivers")
    t_traces, b_traces = {}, {}
    for drv in tb_pick:
        try:
            lap = load_lap(year, event, session, drv)
            thr = [(v * 100 if isinstance(v, (int, float)) and v is not None else None)
                   for v in lap.get("throttle", [])]
            brk = [(v * 100 if isinstance(v, (int, float)) and v is not None else None)
                   for v in lap.get("brake", [])]
            t_traces[drv] = {"x": lap["distance_m"], "y": thr}
            b_traces[drv] = {"x": lap["distance_m"], "y": brk}
        except Exception as e:
            st.warning(f"{drv} overlay failed: {e}")

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.plotly_chart(multi_line("Throttle %", t_traces), use_container_width=True)
    with c2:
        st.plotly_chart(multi_line("Brake %", b_traces), use_container_width=True)

    # ---------------- Turn Telemetry ----------------
    st.markdown("---")
    st.subheader("Turn telemetry")

    def pick_col(df: pd.DataFrame, name: str, alts: list[str]):
        for k in [name] + alts:
            if k in df.columns:
                return df[k]
        return None

    if not map_data or not corners:
        st.info("Map or corners not available.")
    else:
        tnum = st.session_state.get("selected_turn")
        if not tnum:
            st.info("Click a red turn label on the map to inspect Speed / Throttle / Brake near that corner.")
        else:
            st.write(f"Turn **T{tnum}**")
            corner = next((c for c in corners if c["Number"] == tnum), None)
            if not corner:
                st.warning("Corner metadata not found.")
            else:
                cx, cy = float(corner["X"]), float(corner["Y"])
                radius_m = st.slider("Radius around corner (m)", 20, 150, 60, 5, key="turn_radius")

                driver_pool = [ref_driver] + [d for d in cmp_multi if d != ref_driver]
                sel_drivers = st.multiselect("Drivers for turn analysis", driver_pool,
                                             default=driver_pool[:2], key="turn_drivers")

                base = pathlib.Path("data") / str(year) / event / session
                series_speed, series_throttle, series_brake = [], [], []
                for drv in sel_drivers:
                    fp = base / f"{drv}_bestlap.json"
                    if not fp.exists():
                        continue
                    blob = json.loads(fp.read_text(encoding="utf-8"))
                    df = pd.DataFrame(blob)
                    X = pick_col(df, "X", ["x", "x_m"])
                    Y = pick_col(df, "Y", ["y", "y_m"])
                    D = pick_col(df, "Distance", ["distance_m", "dist_m"])
                    S = pick_col(df, "Speed", ["speed_kph"])
                    T = pick_col(df, "Throttle", ["throttle"])
                    B = pick_col(df, "Brake", ["brake"])
                    if X is None or Y is None or D is None:
                        continue
                    X, Y, D = np.asarray(X, float), np.asarray(Y, float), np.asarray(D, float)
                    mask = np.sqrt((X - cx)**2 + (Y - cy)**2) <= radius_m
                    if S is not None:
                        series_speed.append((drv, D[mask], np.asarray(S, float)[mask]))
                    if T is not None:
                        tv = np.asarray(T, float)
                        if np.nanmax(tv) <= 1.0:
                            tv *= 100.0
                        series_throttle.append((drv, D[mask], tv[mask]))
                    if B is not None:
                        bv = np.asarray(B, float)
                        if np.nanmax(bv) <= 1.0:
                            bv *= 100.0
                        series_brake.append((drv, D[mask], bv[mask]))

                def fig_xy(title: str, unit: str) -> go.Figure:
                    f = go.Figure()
                    f.update_layout(title=title, xaxis_title="Distance (m)", yaxis_title=unit,
                                    template="plotly_dark", height=320)
                    return f

                drew = False
                if series_speed:
                    f = fig_xy("Speed near corner", "km/h")
                    for name, x, y in series_speed:
                        f.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
                    st.plotly_chart(f, use_container_width=True); drew = True
                if series_throttle:
                    f = fig_xy("Throttle near corner", "%")
                    for name, x, y in series_throttle:
                        f.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
                    st.plotly_chart(f, use_container_width=True); drew = True
                if series_brake:
                    f = fig_xy("Brake near corner", "%")
                    for name, x, y in series_brake:
                        f.add_trace(go.Scatter(x=x, y=y, mode="lines", name=name))
                    st.plotly_chart(f, use_container_width=True); drew = True
                if not drew:
                    st.info("No telemetry within the chosen radius. Increase radius or pick another turn.")

st.markdown("Tip: legend click toggles traces. Use the camera icon to download PNG.")
