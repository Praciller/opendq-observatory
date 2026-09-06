# Database and query review

Phase 6 adds no migration. The existing `001`–`006` migrations remain the schema authority.

Reviewed query paths:

- ingestion/source status: indexed `ingestion_runs(source_id, started_at DESC)`;
- quality detail: indexed dataset/run paths and `quality_results(evaluation_run_id)`;
- drift history: indexed `drift_evaluation_runs(dataset_id, started_at DESC)` and `drift_results(dataset_id, evaluated_at DESC)`;
- incidents: indexed status/opened, dataset/rule, and event history paths;
- lineage: indexed dataset/node, upstream, and downstream edge paths;
- RCA/AI: indexed incident-created paths and AI fingerprint uniqueness/cache lookup.

The new reliability query uses a bounded 30-day window and aggregates existing run tables; it does not scan raw observations. Public arrays remain bounded by existing route limits. No production `EXPLAIN` or destructive query was run; the local benchmark covers representative query/evaluation paths.
