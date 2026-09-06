# Drift detection

Drift asks whether statistical behavior changed relative to a baseline. It is distinct from data quality: a value can be valid and still move away from its historical distribution.

## Baselines

Trusted CLI creation is explicit:

```powershell
python -m opendq drift baseline create open-meteo
python -m opendq drift baseline list open-meteo
```

Each baseline is immutable after use. A new creation creates version `v2`, deactivates the previous version, and leaves historical results pointing at their original version. Numeric baselines store compact summary statistics and PSI bins; schema baselines store the existing `dataset_versions.schema_json`. Raw observations remain in the observation table and are never copied into a baseline row.

The initial registry covers Open-Meteo temperature, humidity, precipitation, and wind plus USGS magnitude and depth. Numeric checks need at least five baseline and five current observations. Missing history is `BASELINE_UNAVAILABLE` or `INSUFFICIENT_BASELINE`, never a fabricated stable result.

## Methods and status

PSI is calculated with a small epsilon for zero bins. The configured threshold is the significant-shift boundary; half that threshold is WARN. These are conservative, configurable operational defaults, not calibrated probabilities. The persisted details also include mean, median, p95, and normalized median shifts.

The engine supports categorical total variation distance and schema comparison for added, removed, type-changed, and nullability-changed fields. Categorical fixtures are covered even when no production categorical field is enabled.

Results are `STABLE`, `WARN`, `DRIFT`, `ERROR`, or `SKIPPED`. An evaluation run is `SUCCESS`, `PARTIAL`, `FAILED`, or `NO_BASELINE`. `DRIFT` opens or updates one `DATA_DRIFT` incident per dataset/feature/method; `STABLE` resolves it; WARN and SKIPPED preserve state.

## Runtime surfaces

```powershell
python -m opendq drift evaluate open-meteo
python -m opendq drift evaluate usgs
python -m opendq drift evaluate all
```

Read-only surfaces are `/api/drift`, `/api/drift/<dataset>`, and `/drift`. The scheduled six-hour workflow runs ingestion, quality, drift, incident reconciliation, and deterministic RCA in one isolated job.

Production baseline creation is attempted only from legitimate Neon observations. If a feature has insufficient history, the report records `INSUFFICIENT_DATA` and production remains honest.
