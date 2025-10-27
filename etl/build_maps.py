# etl/build_maps.py
from __future__ import annotations
import fastf1, json, pathlib

DATA = pathlib.Path("data")

def export_track(year: int, event: str):
    """Save circuit coordinates, sectors, and corners for a GP."""
    session = fastf1.get_session(year, event, "Q")  # any session works
    session.load()
    circ = session.get_circuit_info()
    out_dir = DATA / str(year) / event
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- track XY
    tel = session.pick_driver(session.drivers[0]).laps.pick_fastest().get_telemetry()
    coords = {"X": tel["X"].tolist(), "Y": tel["Y"].tolist()}
    (out_dir / "track_map.json").write_text(json.dumps(coords), encoding="utf-8")

    # --- sectors
    try:
        sectors = circ["sectors"].to_dict(orient="records")
        (out_dir / "sectors.json").write_text(json.dumps(sectors, indent=2), encoding="utf-8")
    except Exception:
        pass

    # --- corners
    try:
        corners = circ["corners"].to_dict(orient="records")
        (out_dir / "corners.json").write_text(json.dumps(corners, indent=2), encoding="utf-8")
    except Exception:
        pass

    print(f"✅ saved track map for {year} {event}")
    return True

def build_all_tracks(year: int):
    sched = fastf1.get_event_schedule(year, include_testing=False)
    for _, row in sched.iterrows():
        try:
            export_track(year, str(row["EventName"]))
        except Exception as e:
            print("⚠️ failed:", row["EventName"], e)
from etl.build_maps import build_all_tracks
print(f"Building track maps for {year}...")
build_all_tracks(year)