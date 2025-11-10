# streamlit_app.py
from __future__ import annotations
import json, pathlib
from typing import Any, Dict, List, Optional

import fastf1
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
from utils.events import slug_to_event_name, event_name_to_slug


def _reset_filters_and_cache():
    # Clear selection state and any cached data so UI reflects latest code/choices
    for k in [
        "year",
        "event",
        "session",
        "driver_selection",
        "applied_year",
        "applied_event",
        "applied_session",
        "applied_drivers",
        "selected_turn",
        "_last_event",
    ]:
        if k in st.session_state:
            del st.session_state[k]
    try:
        st.cache_data.clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    st.rerun()


def format_timedelta(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        total = value.total_seconds() if hasattr(value, "total_seconds") else float(value)
    except Exception:
        return str(value)
    sign = "-" if total < 0 else ""
    total = abs(total)
    minutes, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{sign}{int(hours):d}:{int(minutes):02d}:{seconds:06.3f}"
    return f"{sign}{int(minutes):02d}:{seconds:06.3f}"


@st.cache_data(show_spinner=False, ttl=3600)
def load_race_summary(year: int, event_slug: str) -> Dict[str, Any]:
    """Fetch race classification + lap snapshots via FastF1 (cached)."""
    event_name = slug_to_event_name(event_slug)
    session = fastf1.get_session(year, event_name, "R")
    session.load(results=True, laps=True, telemetry=False, weather=False)

    summary: Dict[str, Any] = {"results": [], "laps": {}, "fastest": None}

    if session.results is not None and not session.results.empty:
        res = session.results.sort_values("Position")
        for _, row in res.iterrows():
            summary["results"].append({
                "Pos": int(row["Position"]),
                "Driver": row.get("Abbreviation") or row.get("Driver"),
                "Team": row.get("TeamName"),
                "Grid": int(row["GridPosition"]) if pd.notna(row.get("GridPosition")) else None,
                "Status": row.get("Status"),
                "Points": row.get("Points"),
                "Time/Gap": format_timedelta(row.get("Time")),
            })

    laps = session.laps
    if laps is not None and not laps.empty and "Position" in laps.columns:
        lap_groups = laps.dropna(subset=["Position"]).groupby("LapNumber")
        for lap_no, grp in lap_groups:
            snapshot = []
            grp = grp.sort_values("Position")
            for _, row in grp.iterrows():
                snapshot.append({
                    "Pos": int(row["Position"]),
                    "Driver": row.get("Driver") or row.get("Abbreviation"),
                    "LapTime": format_timedelta(row.get("LapTime")),
                    "Compound": row.get("Compound"),
                    "Tyre": None if pd.isna(row.get("TyreLife")) else f"{int(row['TyreLife'])} laps",
                })
            summary["laps"][int(lap_no)] = snapshot

    if laps is not None and not laps.empty:
        try:
            fastest = laps.pick_fastest()
        except Exception:
            fastest = None
        if fastest is not None:
            summary["fastest"] = {
                "Driver": fastest.get("Driver"),
                "Lap": int(fastest.get("LapNumber")),
                "LapTime": format_timedelta(fastest.get("LapTime")),
                "Compound": fastest.get("Compound"),
            }
    return summary


@st.cache_data(show_spinner=False, ttl=3600)
def load_schedule(year: int) -> pd.DataFrame:
    """Cached wrapper around fetch_schedule with graceful failure."""
    try:
        df = fetch_schedule(year)
    except Exception:
        return pd.DataFrame()
    return df

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
st.session_state.setdefault("applied_year", None)
st.session_state.setdefault("applied_event", None)
st.session_state.setdefault("applied_session", None)
st.session_state.setdefault("applied_drivers", [])
st.session_state.setdefault("selected_turn", None)
st.session_state.setdefault("turn_window_m", 120)

# ======================================================
# TABS
# ======================================================
tab_analysis, tab_schedule = st.tabs(["🔍 Analysis", "🗓️ Schedule"])

# ======================================================
# ===============  🗓️  SCHEDULE TAB  ====================
# ======================================================
with tab_schedule:
    st.subheader("Season Schedule")

    years_all = [str(y) for y in (list_years() or list(range(2014, 2025 + 1)))]
    current_year_value = st.session_state["year"] or years_all[0]
    sched_year = st.selectbox(
        "Year",
        years_all,
        index=years_all.index(current_year_value),
        key="sched_year_selector"
    )
    if st.session_state.get("year") != sched_year:
        st.session_state["year"] = sched_year

    df_sched = load_schedule(int(sched_year))
    if df_sched.empty:
        st.info("No schedule data available yet for this year.")
    else:
        ns = next_session(df_sched)
        if ns is not None:
            cols = st.columns([1, 2, 2, 2, 2])
            with cols[0]:
                st.metric("Next", ns['EventName'], help=ns['Session'])
            with cols[1]:
                local_ts = ns['StartLocal']
                local_fmt = local_ts.strftime("%a %d %b %H:%M") if pd.notna(local_ts) else "TBD"
                st.metric("Local time", local_fmt)
            with cols[2]:
                utc_ts = ns['StartUTC']
                utc_fmt = utc_ts.strftime("%a %d %b %H:%M") if pd.notna(utc_ts) else "TBD"
                st.metric("UTC", utc_fmt)
            with cols[3]:
                st.metric("Session", ns['Session'])
            with cols[4]:
                st.metric("Countdown", countdown_str(ns['StartUTC']) if pd.notna(utc_ts) else "TBD")

        st.markdown("### Full Schedule")
        show_local = st.toggle("Show local time", value=True)
        dfv = df_sched.copy()
        def _fmt(series):
            ts = pd.to_datetime(series, utc=False, errors="coerce")
            formatted = ts.dt.strftime("%a %d %b %H:%M")
            return formatted.fillna("TBD")
        dfv["Local"] = _fmt(dfv["StartLocal"])
        dfv["UTC"] = _fmt(dfv["StartUTC"])
        st.dataframe(dfv[["EventName", "Session", "Local" if show_local else "UTC"]],
                     use_container_width=True, height=420)

        st.divider()
        st.markdown("#### Jump to Analysis")

        evs = sorted(df_sched["EventName"].unique().tolist())
        current_event_title = slug_to_event_name(st.session_state["event"]) if st.session_state["event"] else None
        default_event_idx = (
            evs.index(current_event_title) if current_event_title in evs
            else (evs.index(ns["EventName"]) if ns is not None and ns["EventName"] in evs else 0)
        )
        choose_event = st.selectbox("Grand Prix", evs,
                                    index=default_event_idx,
                                    key="sched_jump_event")
        new_event_slug = event_name_to_slug(choose_event)
        if st.session_state.get("event") != new_event_slug:
            st.session_state["event"] = new_event_slug
            st.session_state["selected_turn"] = None

        gp_sessions = df_sched[df_sched["EventName"] == choose_event].sort_values("StartUTC")
        sess_codes = gp_sessions["SessionCode"].tolist()
        session_labels = {row.SessionCode: f"{row.Session} ({row.SessionCode})" for _, row in gp_sessions.iterrows()}
        default_code = st.session_state.get("session")
        if default_code not in sess_codes:
            default_code = "R" if "R" in sess_codes else ("Q" if "Q" in sess_codes else (sess_codes[0] if sess_codes else None))
        if sess_codes:
            choose_session_code = st.selectbox(
                "Session",
                sess_codes,
                index=sess_codes.index(default_code) if default_code in sess_codes else 0,
                key="sched_jump_session",
                format_func=lambda code: session_labels.get(code, code)
            )
            st.session_state["session"] = choose_session_code

# ======================================================
# ===============  🔍 ANALYSIS TAB  =====================
# ======================================================
with tab_analysis:

    # --- Sidebar selectors ---
    years = list_years()
    if not years:
        st.error("No data found. Run ETL to populate /data.")
        st.stop()

    placeholder = "— Select —"

    # Year selector (no default)
    year_options = [placeholder] + years
    year_label = st.sidebar.selectbox(
        "Year",
        year_options,
        index=(year_options.index(st.session_state["year"]) if st.session_state["year"] in years else 0),
        key="year_select"
    )
    year = None if year_label == placeholder else year_label
    st.session_state["year"] = year

    # GP selector
    events = list_events(year) if year else []
    event_options = [placeholder] + events
    event_label = st.sidebar.selectbox(
        "Grand Prix",
        event_options,
        index=(event_options.index(st.session_state["event"]) if st.session_state["event"] in events else 0),
        key="event_select",
        disabled=not bool(year)
    )
    event = None if event_label == placeholder else event_label
    st.session_state["event"] = event

    # Session selector
    sessions = list_sessions(year, event) if (year and event) else []
    session_options = [placeholder] + sessions
    session_label = st.sidebar.selectbox(
        "Session",
        session_options,
        index=(session_options.index(st.session_state["session"]) if st.session_state["session"] in sessions else 0),
        key="session_select",
        disabled=not bool(event)
    )
    session = None if session_label == placeholder else session_label
    st.session_state["session"] = session

    # Drivers (no default). Allow picking 1+ and we’ll handle comparisons accordingly.
    drivers = list_drivers(year, event, session) if (year and event and session) else []
    stored_selection = [d for d in st.session_state.get("driver_selection", []) if d in drivers]
    driver_selection = st.sidebar.multiselect(
        "Drivers (first = reference)",
        drivers,
        default=stored_selection,
        key="driver_selection",
        disabled=not bool(session)
    )

    # Apply/Reset buttons in the sidebar
    can_apply = bool(year and event and session and driver_selection)
    if st.sidebar.button("Apply", type="primary", disabled=not can_apply, use_container_width=True):
        st.session_state["applied_year"] = year
        st.session_state["applied_event"] = event
        st.session_state["applied_session"] = session
        st.session_state["applied_drivers"] = driver_selection
        st.rerun()

    if st.sidebar.button("Reset filters", use_container_width=True):
        _reset_filters_and_cache()

    # Use applied filters for analysis; if none, prompt and stop.
    applied_year = st.session_state.get("applied_year")
    applied_event = st.session_state.get("applied_event")
    applied_session = st.session_state.get("applied_session")
    applied_drivers = st.session_state.get("applied_drivers", [])

    if not (applied_year and applied_event and applied_session and applied_drivers):
        st.info("Pick Year, Grand Prix, Session, select drivers, then click Apply to load analysis.")
        st.stop()

    year = applied_year
    event = applied_event
    session = applied_session
    driver_selection = applied_drivers

    ref_driver = driver_selection[0]
    cmp_multi = driver_selection[1:]

    # --- Schedule preview ---
    sched_preview = load_schedule(int(year))
    if sched_preview.empty:
        st.info("Schedule data unavailable for this season (connect FastF1 or add local fallback).")
    else:
        ns_preview = next_session(sched_preview)
        if ns_preview is not None:
            cols = st.columns([1, 1, 1, 1])
            cols[0].metric("Next GP", ns_preview["EventName"])
            cols[1].metric("Session", ns_preview["Session"])
            cols[2].metric(
                "Local",
                ns_preview["StartLocal"].strftime("%a %d %b %H:%M") if pd.notna(ns_preview["StartLocal"]) else "TBD"
            )
            cols[3].metric(
                "UTC",
                ns_preview["StartUTC"].strftime("%a %d %b %H:%M") if pd.notna(ns_preview["StartUTC"]) else "TBD"
            )
        with st.expander(f"{year} season schedule", expanded=False):
            df_preview = sched_preview.copy()
            def _fmt(series):
                ts = pd.to_datetime(series, errors="coerce")
                formatted = ts.dt.strftime("%a %d %b %H:%M")
                return formatted.fillna("TBD")
            df_preview["Local"] = _fmt(df_preview["StartLocal"])
            df_preview["UTC"] = _fmt(df_preview["StartUTC"])
            st.dataframe(
                df_preview[["EventName", "Session", "Local", "UTC"]],
                use_container_width=True,
                height=280
            )
        st.divider()

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
    t_traces, b_traces = {}, {}
    for drv in driver_selection:
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

    zoom_window = st.session_state.get("turn_window_m", 120)
    zoom_range = None
    selected_turn = st.session_state.get("selected_turn")
    if selected_turn and corners:
        corner = next((c for c in corners if c["Number"] == selected_turn), None)
        if corner and "Distance" in corner:
            try:
                dist = float(corner["Distance"])
                zoom_range = (max(0.0, dist - zoom_window), dist + zoom_window)
            except (TypeError, ValueError):
                zoom_range = None

    c1, c2 = st.columns(2, gap="large")
    with c1:
        if t_traces:
            st.plotly_chart(
                multi_line("Throttle %", t_traces, yaxis_title="%", xaxis_range=zoom_range),
                use_container_width=True
            )
            if zoom_range:
                st.caption(f"Zoomed to +/-{zoom_window} m around T{selected_turn}.")
        else:
            st.info("No throttle telemetry for selected drivers.")
    with c2:
        if b_traces:
            st.plotly_chart(
                multi_line("Brake %", b_traces, yaxis_title="%", xaxis_range=zoom_range),
                use_container_width=True
            )
        else:
            st.info("No brake telemetry for selected drivers.")

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
                radius_m = st.slider("Radius around corner (m)", 20, 150,
                                     st.session_state.get("turn_radius", 60), 5, key="turn_radius")
                st.slider("Distance window for charts (m)", 40, 300,
                          st.session_state.get("turn_window_m", 120), 10, key="turn_window_m")

                base = pathlib.Path("data") / str(year) / event / session
                series_speed, series_throttle, series_brake = [], [], []
                for drv in driver_selection:
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

    if session.upper() == "R":
        st.markdown("---")
        st.subheader("Race recap")
        try:
            race_summary = load_race_summary(int(year), event)
        except Exception as exc:
            st.info(f"Race summary unavailable: {exc}")
        else:
            results = race_summary.get("results", [])
            fastest = race_summary.get("fastest")
            if results:
                winner = results[0]
                cols = st.columns(3)
                cols[0].metric("Winner", f"{winner.get('Driver')} ({winner.get('Team')})",
                               help=f"Grid {winner.get('Grid')}")
                cols[1].metric("Points", winner.get("Points", 0))
                if fastest:
                    cols[2].metric("Fastest lap",
                                   f"L{fastest.get('Lap')} {fastest.get('Driver')}",
                                   help=f"{fastest.get('LapTime')} on {fastest.get('Compound')}")
                else:
                    cols[2].metric("Fastest lap", "n/a")
                st.dataframe(pd.DataFrame(results), hide_index=True, use_container_width=True)
            else:
                st.info("No official classification available for this race.")

            lap_snaps = race_summary.get("laps", {})
            if lap_snaps:
                lap_numbers = sorted(lap_snaps.keys())
                if st.session_state.get("race_lap_slider") not in lap_numbers:
                    st.session_state["race_lap_slider"] = lap_numbers[-1]
                lap_choice = st.slider("Lap to inspect", lap_numbers[0], lap_numbers[-1],
                                       key="race_lap_slider")
                st.dataframe(pd.DataFrame(lap_snaps.get(lap_choice, [])),
                             hide_index=True, use_container_width=True)
            else:
                st.info("Lap-by-lap placement data unavailable for this session.")

st.markdown("Tip: legend click toggles traces. Use the camera icon to download PNG.")
