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

`FAIL` creates `DATA_QUALITY`; `ERROR` creates `EVALUATION_ERROR`. Severity is copied from the configured quality rule. Summaries and evidence are deterministic templates containing the persisted observed/expected values.

## Mutation boundary

The public application and all public API routes are read-only. A trusted operator can use `python -m opendq incident acknowledge <id>` to move an OPEN incident to ACKNOWLEDGED. There is intentionally no public acknowledge, resolve, create, or update endpoint until authentication is designed.

## Evidence and impact

An incident references its first/latest evaluation run and quality result. When first opened, the incident captures the current bounded downstream lineage traversal in `incident_impacts`. Repeated observations do not overwrite the initial snapshot, preserving historical explainability.

The `/api/incidents` endpoint supports bounded status, dataset, and severity filters. `/api/incidents/<id>` exposes lifecycle events, deterministic evidence, and captured impact. `/incidents` and `/incidents/<id>` render the same persisted data.
