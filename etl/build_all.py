from __future__ import annotations
import os, sys, json, time, pathlib, traceback
from typing import Dict, Any, Optional, List
import pandas as pd

print(">> import fastf1 + cache init")
import fastf1
CACHE_PATH = os.path.join(os.getcwd(), "fastf1_cache")
os.makedirs(CACHE_PATH, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_PATH)

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
def _ensure(p: pathlib.Path): p.mkdir(parents=True, exist_ok=True)

def _safe_float(v):
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)): return None
        return float(v)
    except Exception:
        return None

def _lap_df_to_json(df: pd.DataFrame) -> Dict[str, Any]:
    for col in ["Distance","Speed","Time","Throttle","Brake","nGear","DRS"]:
        if col not in df.columns: df[col] = pd.Series([None]*len(df))
    df = df.dropna(subset=["Distance","Speed"])
    if df.empty: return {}
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

def _sanitize(name: str) -> str: return name.lower().replace(" ", "-")

def _best_lap_blob(session, drv_abbr: str) -> Optional[Dict[str, Any]]:
    laps = session.laps.pick_drivers([drv_abbr])
    if laps is None or len(laps) == 0:
        return None
    fastest = laps.pick_fastest()
    if fastest is None:
        return None
    try:
        tel = fastest.get_telemetry()
    except Exception:
        return None
    blob = _lap_df_to_json(tel)
    if not blob: return None
    blob["driver"] = drv_abbr
    blob["lapNumber"] = int(fastest["LapNumber"])
    return blob

def build(year_from: int, year_to: int):
    print(f">> BUILD {year_from}-{year_to}")
    for year in range(year_from, year_to + 1):
        print(f"== Year {year}")
        try:
            sched = fastf1.get_event_schedule(year, include_testing=False)
        except Exception as e:
            print("schedule error:", e); continue

        for _, ev in sched.iterrows():
            evname = str(ev["EventName"])
            for sess in ["FP1","FP2","FP3","SQ","SS","Q","R"]:
                try:
                    s = fastf1.get_session(year, evname, sess)
                    s.load(telemetry=True, laps=True, weather=False)
                except Exception:
                    continue

                try:
                    drivers = sorted(set(s.laps["Driver"].dropna().tolist()))
                except Exception:
                    continue

                wrote_any = False
                for drv in drivers:
                    try:
                        blob = _best_lap_blob(s, drv)
                        if not blob: 
                            continue
                        out = DATA / str(year) / _sanitize(evname) / sess / f"{drv}_bestlap.json"
                        _ensure(out.parent)
                        out.write_text(json.dumps(blob, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                        print("Wrote", out)
                        wrote_any = True
                    except Exception:
                        traceback.print_exc()
                        continue
                if wrote_any:
                    print(f"-- {year} {evname} {sess}: OK")

if __name__ == "__main__":
    yf = int(sys.argv[1]) if len(sys.argv) >= 2 else 2018
    yt = int(sys.argv[2]) if len(sys.argv) >= 3 else yf
    build(yf, yt)
