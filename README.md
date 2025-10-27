
This readme covers Windows and macOS/Linux end to end, including setup, running the Streamlit app, building data, race analysis, weekly auto refresh, GitHub Desktop, and troubleshooting.


# F1 Lap Explorer

Interactive F1 analytics web app.
Practice and Qualifying use best-lap telemetry.
Race adds full lap-by-lap analysis with tyres, stints, positions, and gap to leader.

## Features

* Compare drivers on lap delta vs distance and speed traces
* Throttle and brake overlays
* Race tab with position vs lap, tyre stints, and gap to leader
* Local cache for FastF1 data
* JSON data in `data/` for reproducible dashboards
* Optional weekly refresh on GitHub Actions

---

## Repo structure

```
Formula1/
├─ streamlit_app.py
├─ requirements.txt
├─ .gitignore
├─ README.md
├─ utils/
│  ├─ data_loader.py
│  ├─ lap_delta.py
│  └─ plotting.py
├─ etl/
│  ├─ make_dataset.py         # small sample per-session builder
│  ├─ build_all.py            # bulk best-lap builder for many seasons
│  └─ build_race.py           # full race export (lap-by-lap)
├─ data/                      # JSON outputs live here
│  └─ .gitkeep
└─ fastf1_cache/              # local cache (ignored by git)
```

`.gitignore` should keep `.venv/`, `fastf1_cache/`, `__pycache__/`, editor folders, and all non-JSON under `data/`.

---

## Prerequisites

* Python 3.11 or newer
* Git
* Visual Studio Code with the Python extension
* Streamlit Community Cloud account if you plan to deploy

---

## Quick start on Windows (PowerShell)

```powershell
# 1) open a terminal
cd C:\Users\<you>\Documents\GitHub
git clone https://github.com/<you>/Formula1.git
cd .\Formula1

# 2) create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

# 3) install dependencies
pip install -r requirements.txt

# 4) generate a small sample dataset
python .\etl\make_dataset.py .\etl\config.example.yaml

# 5) run the app
streamlit run .\streamlit_app.py
# open http://localhost:8501
```

Keep Streamlit running.
Open a second terminal tab in VS Code to build more data:

```powershell
# 6) activate venv in the new tab
.\.venv\Scripts\Activate.ps1

# 7) build proven seasons first
python .\etl\build_all.py 2020 2020
python .\etl\build_all.py 2021 2023

# 8) build race data for an event
python - << 'PY'
from etl.build_race import export_race
print(export_race(2020, "Italian Grand Prix"))
PY
```

Press `r` in the Streamlit browser tab or enable Always rerun to refresh menus.

---

## Quick start on macOS or Linux (bash)

```bash
# 1) terminal
cd ~/Projects
git clone https://github.com/<you>/Formula1.git
cd Formula1

# 2) venv
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

# 3) install
pip install -r requirements.txt

# 4) sample dataset
python etl/make_dataset.py etl/config.example.yaml

# 5) run app
streamlit run streamlit_app.py
# open http://localhost:8501
```

Build more data in a second terminal:

```bash
source .venv/bin/activate
python etl/build_all.py 2020 2020
python etl/build_all.py 2021 2023

python - << 'PY'
from etl.build_race import export_race
print(export_race(2020, "Italian Grand Prix"))
PY
```

---

## What each ETL does

* `etl/make_dataset.py`
  Small sample from `etl/config.example.yaml`.
  Writes per-driver best-lap telemetry JSON for selected sessions.

* `etl/build_all.py`
  Crawls a year range.
  Writes per-driver best-lap JSON for FP1, FP2, FP3, SQ, SS, Q, R where telemetry exists.
  Telemetry is most reliable from 2018 onward.

* `etl/build_race.py`
  Writes full lap-by-lap JSON per driver for Race only: lap times, sectors, position, pit flags, compound, tyre life, stints, cumulative time.
  Also writes `session_summary.json` with simple classification and track status timeline.

---

## Data locations

* Best-lap telemetry
  `data/<year>/<grand-prix>/<session>/<DRIVER>_bestlap.json`

* Race lap-by-lap
  `data/<year>/<grand-prix>/R/<DRIVER>_race.json`
  `data/<year>/<grand-prix>/R/session_summary.json`

Grand Prix folder names are lowercase and hyphenated.
Example: `data/2020/italian-grand-prix/Q/VER_bestlap.json`

---

## Using GitHub Desktop

* Open the repo in GitHub Desktop
* Stage only source files, JSON outputs, and workflow files
* Right-click `.venv/` and `fastf1_cache/` to Ignore if they appear
* Commit messages should be short and focused

  * `feat: add race tab`
  * `fix(etl): skip drivers with missing telemetry`
  * `chore: weekly Actions refresh`

---

## Weekly auto refresh on GitHub Actions

Create `.github/workflows/weekly_data.yml`:

```yaml
name: Weekly F1 data refresh
on:
  schedule:
    - cron: "0 4 * * 1"
  workflow_dispatch:

jobs:
  refresh:
    runs-on: ubuntu-latest
    permissions: { contents: write }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Build current season
        run: |
          python - << 'PY'
          import time, fastf1
          from etl.build_all import build as build_all
          from etl.build_race import export_race
          year = int(time.strftime("%Y"))
          build_all(year, year)
          sched = fastf1.get_event_schedule(year, include_testing=False)
          for _, ev in sched.iterrows():
              evname = str(ev["EventName"])
              try:
                  export_race(year, evname)
                  print("race exported:", year, evname)
              except Exception as e:
                  print("race export failed:", year, evname, e)
          PY
      - name: Commit new data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data
          git commit -m "chore(data): weekly refresh" || echo "nothing to commit"
          git push
```

Push to `main`.
Actions will run every Monday 04:00 UTC and on manual dispatch.

---

## Deployment to Streamlit Community Cloud

1. Push repo to GitHub
2. Go to [https://share.streamlit.io](https://share.streamlit.io)
3. New app
4. Pick your repo, branch `main`, file `streamlit_app.py`
5. Python 3.11
6. Deploy

---

## Troubleshooting

* `ERROR: Could not open requirements file`
  Create `requirements.txt` in repo root and run `pip install -r requirements.txt`.

* `Cache directory does not exist`
  The ETL sets it automatically to `fastf1_cache/`.
  If needed, create it: `mkdir fastf1_cache`.

* No JSON appears under `data/`
  Run a small test:
  `python etl/make_dataset.py etl/config.example.yaml`
  Then check count:
  Windows
  `Get-ChildItem -Recurse .\data -Filter *_bestlap.json | Measure-Object`
  macOS/Linux
  `find data -name "*_bestlap.json" | wc -l`

* Streamlit sees only one year
  You probably built only one season. Run `build_all.py` for more ranges and refresh Streamlit.

* 2014–2017 telemetry
  Per-distance telemetry for best-lap charts is incomplete in older seasons. Races still provide usable lap tables and positions for many events. Use `build_race.py` for those.

---

## FAQ

**Why best lap for non-race sessions**
Users compare peak pace and speed traces. That is what telemetry supports best across many sessions.

**Why full race JSONs**
Race analysis needs tyres, stints, positions, gaps, and cumulative times per lap, not just one lap.

**Can I run the builders while Streamlit is open**
Yes. Open a second terminal tab, activate the venv, run builders, then press `r` in the browser.

**Can I delete old data and rebuild**
Yes. If you used a resumable state file, remove it before a clean rebuild.

---

## References

* FastF1 documentation
  [https://docs.fastf1.dev](https://docs.fastf1.dev)

* Cole Nussbaumer Knaflic, Storytelling with Data
  [https://www.storytellingwithdata.com/books](https://www.storytellingwithdata.com/books)

* Edward R. Tufte, The Visual Display of Quantitative Information
  [https://www.edwardtufte.com/tufte/books_vdqi](https://www.edwardtufte.com/tufte/books_vdqi)

* Robert C. Martin, Clean Code
  [https://www.informit.com/store/clean-code-a-handbook-of-agile-software-craftsmanship-9780132350884](https://www.informit.com/store/clean-code-a-handbook-of-agile-software-craftsmanship-9780132350884)

* Martin Fowler, Refactoring
  [https://martinfowler.com/books/refactoring.html](https://martinfowler.com/books/refactoring.html)

* Martin Kleppmann, Designing Data-Intensive Applications
  [https://dataintensive.net](https://dataintensive.net)

