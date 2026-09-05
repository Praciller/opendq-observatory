# Data quality engine

Phase 2 evaluates the normalized observations already persisted by Open-Meteo and USGS ingestion. It is deterministic-first: rules use explicit configuration and SQL-backed observations, with no machine learning, public-internet calls, or fabricated history.

## Dimensions and statuses

The initial rules cover:

- **Freshness:** newest observation age against a configured maximum, using observation time rather than ingestion time.
- **Completeness:** null rate for a configured canonical field.
- **Uniqueness:** logical weather key `(latitude, longitude, observed_at)` or earthquake `event_id`; this complements database constraints.
- **Validity:** broad numeric sanity/range checks such as humidity `0–100`, precipitation `>= 0`, coordinates, magnitude, and depth.
- **Timestamp continuity:** regular weather sample intervals and allowed maximum gap. This is not applied to irregular earthquake events.
- **Volume anomaly:** latest received volume against a rolling median of recent successful/no-change runs.

Each result is one of `PASS`, `WARN`, `FAIL`, `ERROR`, or `SKIPPED`:

- `FAIL` means the data was evaluated and violated a configured threshold.
- `ERROR` means the rule could not execute; it is not silently converted into a data failure.
- `SKIPPED` means the rule was not meaningfully applicable, for example insufficient volume history or an irregular event dataset.

Every result stores what was checked, observed and expected values, affected/evaluated record counts, severity, and evaluation time.

## Score

The score is a summary, not the source of truth:

```text
PASS = 1.0
WARN = 0.5
FAIL = 0.0
score = average(scored results) * 100
```

`ERROR` and `SKIPPED` are excluded from the denominator and remain visible in the result counts. If no result can be scored, the score is `null`, never an invented zero or historical value.

## Dataset rules

Open-Meteo receives freshness, temperature completeness/range, humidity range, precipitation non-negative, timestamp continuity, logical uniqueness, and volume rules.

USGS receives freshness, event identifier completeness/uniqueness, magnitude, latitude, longitude, depth, and volume rules. Periodic timestamp-gap logic is intentionally not applied to earthquakes.

## Evaluation lifecycle

```text
ingestion SUCCESS or NO_CHANGE
        ↓
quality evaluation run RUNNING
        ↓
individual rule results persisted
        ↓
quality evaluation run SUCCESS
        ↓
incident reconciliation from persisted results
```

An ingestion run remains successful when a quality rule returns `FAIL`. A quality-engine runtime failure is recorded as a terminal evaluation `FAILED` run, while a per-rule exception is stored as an `ERROR` result when the evaluation can otherwise complete.

## CLI and API

```powershell
python -m opendq quality evaluate open-meteo
python -m opendq quality evaluate usgs
python -m opendq quality evaluate all
```

The web surface exposes `/api/quality`, `/api/quality/sources`, `/quality`, `/api/incidents`, and `/api/lineage`. These endpoints return persisted results only and never expose connection strings, raw SQL errors, or stack traces.

## Incident mapping

Quality evidence is not itself an incident. After a completed evaluation, reconciliation applies this deterministic mapping:

- `FAIL` opens or updates `DATA_QUALITY` for the dataset/rule using the configured rule severity.
- `ERROR` opens or updates `EVALUATION_ERROR`; runtime evaluation failure is not treated as healthy data.
- `PASS` resolves an active incident for the dataset/rule, including an acknowledged incident.
- `WARN` and `SKIPPED` do not create incidents; `SKIPPED` also does not resolve an existing incident because it means not evaluated.

The quality engine remains responsible for whether a rule passes. The incident engine is responsible only for the stateful operational interpretation and event history. AI root-cause analysis, drift detection, and streaming remain deferred.
