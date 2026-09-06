# Incidents

Phase 3 incidents are deterministic stateful interpretations of persisted quality evidence. They are not AI explanations and do not infer cross-rule root causes.

## Lifecycle

An incident is keyed by `dataset_id + rule_id`. PostgreSQL enforces one active incident in `OPEN` or `ACKNOWLEDGED` state for that key. A repeated failure updates the same incident, increments `occurrence_count`, updates `last_seen_at`, and appends an `OBSERVED_AGAIN` event. A resolved condition that fails later creates a new historical incident.

```text
FAIL/ERROR → OPEN → ACKNOWLEDGED → RESOLVED
                 ↘ repeated evidence updates the same incident
PASS       → resolve OPEN or ACKNOWLEDGED
WARN       → no transition
SKIPPED    → no transition, including no automatic recovery
```

`FAIL` creates `DATA_QUALITY`; `ERROR` creates `EVALUATION_ERROR`; `DRIFT` creates `DATA_DRIFT`. Stable drift resolves an active drift incident, while WARN and SKIPPED preserve state. Severity is copied from the configured rule or explicit drift registry. Summaries and evidence are deterministic templates containing persisted metrics, thresholds, and windows.

## Mutation boundary

The public application and all public API routes are read-only. A trusted operator can use `python -m opendq incident acknowledge <id>` to move an OPEN incident to ACKNOWLEDGED. There is intentionally no public acknowledge, resolve, create, or update endpoint until authentication is designed.

## Evidence and impact

An incident references its first/latest evaluation run and quality result. When first opened, the incident captures the current bounded downstream lineage traversal in `incident_impacts`. Repeated observations do not overwrite the initial snapshot, preserving historical explainability.

The `/api/incidents` endpoint supports bounded status, dataset, and severity filters. `/api/incidents/<id>` exposes lifecycle events, deterministic evidence, captured impact, and `/api/incidents/<id>/rca` exposes the latest persisted RCA. `/api/incidents/<id>/ai` only reads the latest persisted optional explanation; it never triggers inference. `/incidents` and `/incidents/<id>` render the same data.

## Deterministic RCA

When an incident opens or receives meaningful new evidence, the pipeline ranks controlled causes such as `UPSTREAM_SOURCE_FAILURE`, `SCHEMA_CHANGE`, `FRESHNESS_DELAY`, `TIMESTAMP_GAP`, `INVALID_VALUES`, `VOLUME_CHANGE`, `DISTRIBUTION_SHIFT`, `DATABASE_OR_PIPELINE_ERROR`, and `UNKNOWN`. Direct evidence has the highest weight; temporal/dataset alignment and upstream lineage context add bounded support. Scores and evidence IDs are persisted with `deterministic-rca-v1`. The result says “probable cause,” not “proven root cause.”

## Optional AI explanation

The AI Incident Copilot is subordinate to deterministic RCA. It receives a
bounded public-only evidence DTO and returns a schema-validated explanation
with grounded evidence IDs, suggested investigation steps, and explicit
uncertainties. If providers are disabled or fail, the pipeline persists a
deterministic fallback. AI output never changes incident state or RCA.
