# F1 Insights

Community-led Formula 1 analytical workspace focused on **transformative use**:
- Post-race analysis
- User-uploaded telemetry comparison
- Strategy simulation using open/historical data

## Legal posture (important)

This project is built to avoid replicating official live timing/broadcast products.

1. No live timing tower replication
2. No rebroadcast of proprietary streams
3. User upload mode requires users to confirm legal access to their own data exports
4. Open-data mode uses publicly accessible historical/community sources
5. Outputs are secondary analytics and derived insights

This is not legal advice.

## Project structure

- `app/`: Streamlit UI and pages
- `src/f1_insights/data`: ingestion, validation, normalization
- `src/f1_insights/analysis`: analytics engines
- `src/f1_insights/simulation`: strategy simulation
- `src/f1_insights/legal`: compliance rules and text

## Quick start

```bash
cd F1_Insights
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/Home.py
```

## Data standards

Two standardized schemas are supported:

1. **User Telemetry Standard** (`TelemetryRecord`)
2. **Open Historical Race Standard** (`HistoricalLapRecord`)

They are intentionally separate to avoid mixing provenance and legal risk.
