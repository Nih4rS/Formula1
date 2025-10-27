import json, pathlib, sys, traceback
from typing import Dict, Any, Optional
import pandas as pd
import yaml

try:
    import fastf1
    import os
    CACHE_PATH = os.path.join(os.getcwd(), "fastf1_cache")
    os.makedirs(CACHE_PATH, exist_ok=True)
    fastf1.Cache.enable_cache(CACHE_PATH)

except Exception as e:
    print("FastF1 init failed:", e)
    sys.exit(2)

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def _safe_float(v) -> Optional[float]:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return float(v)
    except Exception:
        return None

def _lap_df_to_json(df: pd.DataFrame) -> Dict[str, Any]:
    # defensive columns
    for col in ["Distance","Speed","Time","Throttle","Brake","nGear","DRS"]:
        if col not in df.columns:
            df[col] = pd.Series([None]*len(df))
    df = df.dropna(subset=["Distance","Speed"])
    t0 = df["Time"].iloc[0]
    cum = (df["Time"] - t0).dt.total_seconds()
    return {
        "distance_m":  [_safe_float(x) for x in df["Distance"].tolist()],
        "speed_kph":   [_safe_float(x) for x in df["Speed"].tolist()],
        "throttle":    [_safe_float(x) for x in df["Throttle"].tolist()],
        "brake":       [_safe_float(x) for x in df["Brake"].tolist()],
        "gear":        [int(x) if pd.notna(x) else None for x in df["nGear"].tolist()],
        "drs":         [int(x) if pd.notna(x) else None for x in df["DRS"].tolist()],
        "cum_lap_time_s": [_safe_float(x) for x in cum.tolist()]
    }

def _best_lap_json(session, driver: str) -> Optional[Dict[str, Any]]:
    # use new API; returns empty if no laps
    laps = session.laps.pick_drivers([driver])
    if laps is None or len(laps) == 0 or laps.pick_fastest() is None:
        return None
    fastest = laps.pick_fastest()
    # guard: sometimes fastest is present but telemetry is unavailable
    try:
        tel = fastest.get_telemetry()
    except Exception:
        return None
    out = _lap_df_to_json(tel)
    out["driver"] = driver
    out["lapNumber"] = int(fastest["LapNumber"])
    return out

def _ensure(p: pathlib.Path): p.mkdir(parents=True, exist_ok=True)

def main(cfg_path: str):
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    year = cfg["year"]
    for ev in cfg["events"]:
        evname = ev["name"]
        for sess in ev["sessions"]:
            try:
                s = fastf1.get_session(year, evname, sess)
                s.load(telemetry=True, laps=True, weather=False)
            except Exception:
                print(f"Failed loading {year} {evname} {sess}")
                traceback.print_exc()
                continue
            for drv in ev["drivers"]:
                try:
                    data_blob = _best_lap_json(s, drv)
                    if not data_blob:
                        print(f"Skip: no valid lap/telemetry for {drv} in {year} {evname} {sess}")
                        continue
                    target = DATA / str(year) / evname.lower().replace(" ", "-") / sess / f"{drv}_bestlap.json"
                    _ensure(target.parent)
                    with open(target, "w", encoding="utf-8") as f:
                        json.dump(data_blob, f, ensure_ascii=False, separators=(",", ":"))
                    print("Wrote", target)
                except Exception:
                    print(f"Driver {drv} failed for {year} {evname} {sess}")
                    traceback.print_exc()

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(pathlib.Path(__file__).with_name("config.example.yaml")))
