# Data model

The initial migration creates five tables:

- `sources` stores stable source slugs and public metadata.
- `datasets` belongs to a source and identifies a logical normalized dataset.
- `dataset_versions` records schema version, hash, and reviewable JSON.
- `ingestion_runs` records the lifecycle, counters, timestamps, and sanitized failure details for every started run.
- `raw_observations` stores selected canonical fields plus compact source payload/provenance for reproducibility.

Foreign keys and indexes support source-to-dataset lookup, recent run queries, and observation time queries. Unique constraints prevent duplicate source/dataset slugs, duplicate weather records for a dataset/location/timestamp, and duplicate USGS event IDs for a dataset. Upserts rely on these database constraints rather than application-only checks.

The Phase 3 migration adds incident and lineage tables described below. Drift tables remain deferred.

## Phase 2 quality tables

The Phase 2 migration adds:

- `quality_rules`, which stores dataset-scoped rule identity, dimension, rule type, severity, enabled state, and JSON configuration. Executable code is never stored in the database.
- `quality_evaluation_runs`, which records the terminal lifecycle, trigger, per-status counts, optional score, and sanitized engine errors.
- `quality_results`, which links a rule to an evaluation run and stores status, observed/expected JSON values, affected/evaluated record counts, details, and evaluation time.

The score is denormalized on `quality_evaluation_runs` for efficient dashboard reads; individual `quality_results` remain authoritative. Foreign keys and unique `(evaluation_run_id, rule_id)` prevent orphaned or repeated results within one evaluation.

## Phase 3 incident and lineage tables

- `incidents` stores one stateful condition per dataset/rule, with controlled kind, status, severity, lifecycle timestamps, evidence, and quality-result references. A partial unique index enforces one active (`OPEN` or `ACKNOWLEDGED`) incident per dataset/rule while resolved history remains available.
- `incident_events` stores meaningful lifecycle/evidence events: `OPENED`, `OBSERVED_AGAIN`, `ACKNOWLEDGED`, and `RESOLVED`.
- `lineage_nodes` stores stable provider-neutral source, dataset, process, API, and dashboard keys.
- `lineage_edges` stores a small controlled edge vocabulary and rejects self-edges and exact duplicates.
- `incident_impacts` stores the shortest downstream path captured when an incident is first opened. It is unique per incident/node and is not overwritten by repeated observations.

The graph seed is repeatable and idempotent. Traversal is a bounded breadth-first search with cycle protection and a maximum depth of ten. Public APIs and pages read these tables; only the trusted pipeline/CLI workflow mutates incident state.

