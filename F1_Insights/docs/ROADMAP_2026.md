# F1 Insights Roadmap (2026)

## Vision

Build a community-led, legally safer Formula 1 analytics ecosystem focused on **transformative insights** rather than broadcast replication.

## Data modes (kept separate by design)

1. **User Telemetry Upload Mode**
   - Data source: user-provided CSV/Parquet exports
   - Requirement: legal attestation by user
   - Purpose: driver style comparisons, post-race deep dives

2. **Open Historical Mode**
   - Data source: open/public historical endpoints (e.g., OpenF1)
   - Purpose: fuel-corrected pace, stint degradation, strategy simulation

## Standardized schemas

- `TelemetryRecord` (upload mode)
- `HistoricalLapRecord` (open mode)

Schemas are intentionally not merged to preserve data provenance and compliance boundaries.

## Current MVP implemented

- Streamlit multipage UI
- Upload pipeline with normalization + schema validation
- Open historical lap fetch + normalization + validation
- Fuel-corrected pace trend model
- Driver telemetry binning + speed delta comparison
- Monte Carlo pit strategy simulator
- Dedicated compliance guardrails page

## Next build phases

### Phase 1: Advanced analytics
- Bayesian state-space tire model with pit-reset state transitions
- Undercut/overcut opportunity scoring
- Dirty-air proximity penalty model (distance-based coefficient)

### Phase 2: Simulation intelligence
- Monte Carlo race outcome distributions with safety-car priors
- Q-learning baseline strategy agent
- PPO extension for non-stationary race conditions

### Phase 3: Community workflows
- User profile and saved sessions
- Sim-racing telemetry upload adapters
- Shared insight notebooks and reproducible reports

## Compliance-first product rules

- Never replicate official live timing tower
- Never rebroadcast proprietary media streams
- No direct betting feed output
- Highlight all outputs as derived analytics
- Keep legal attestation gate enabled for user uploads

## Suggested deployment progression

1. Local Streamlit development
2. Streamlit Community Cloud private preview
3. Add managed PostgreSQL/Timescale for persistent results
4. Add auth and storage controls for user uploads

## Note

This roadmap supports technical planning and community governance. It is not legal advice.
