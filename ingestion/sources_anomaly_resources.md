# Anomaly Detection Resources (Trimmed for DOGEGPT)

**Aim:** Practical tools for *government budget/audit* anomaly detection.

## Libraries (use now)
- **PyOD** – Mega-collection of outlier detectors (IsolationForest, LOF, AutoEncoders, ECOD). Great for tabular & cross-sectional anomalies.
- **ADTK** – Time-series detection toolkit (level shifts, volatility shifts, seasonal outliers). Ideal for monthly/quarterly spend series.

## Benchmarks / Datasets (for patterns & testing)
- **NAB (Numenta Anomaly Benchmark)** – Time-series anomalies with labels (concepts for alert scoring).
- **Yahoo S5** – Real + synthetic time series with injected anomalies.
- **ODDS (Outlier Detection DataSets)** – Tabular datasets to sanity-check your pipeline.
- **UCI** subsets (e.g., credit card fraud) – Good to validate detectors on skewed, sparse anomalies.

## Patterns to look for in county budgets
- **Contextual spikes** – Department spends within normal annual total, but **specific month/line** jumps (overtime, emergency purchase).
- **Collective anomalies** – Series of moderate spikes across related accounts → bigger pattern (vendor steering, reclassification waves).
- **Composition breaks** – % mix across categories for a department changes drastically YoY without matching policy/external events.
- **Benford deviations** – Not definitive, but useful smoke test on *invented numbers* (use on claims/reimbursements, not totals).

## First pass algorithms (choose by data)
- **Annual only**: Robust z-score on YoY deltas + PyOD (IsolationForest, ECOD) on department/category totals and composition vectors.
- **Monthly/Quarterly**: ADTK LevelShiftAD, PersistAD, SeasonalityAD + PyOD on per-period features.
- **Explainability**: Prefer tree-based (IsolationForest) and simple stats for first videos. Deep nets later if we need them.

> Keep it simple, reproducible, and explainable. The audience must *see* the “weird.”
