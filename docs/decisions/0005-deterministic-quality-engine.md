# ADR 0005: Deterministic quality evaluation after ingestion

## Status

Accepted for Phase 2.

## Decision

Evaluate explicit, dataset-scoped quality rules after a successful or no-change ingestion and persist both the evaluation run and each rule result in PostgreSQL. Keep ingestion health separate from data-quality health.

The first rules cover freshness, completeness, uniqueness, validity/range, timestamp continuity for regularly sampled weather, and a rolling-median volume check. The score is a transparent summary of PASS/WARN/FAIL results; SKIPPED and ERROR remain visible and are not treated as PASS.

## Why

This keeps the portfolio project explainable, testable, and free-tier efficient. PostgreSQL remains the source of truth, rule configuration is reviewable JSON rather than executable code, and a data-quality failure does not incorrectly claim that source ingestion failed.

## Rejected alternatives

- ML anomaly detection: unnecessary for the first deterministic baseline and difficult to explain with small free-tier history.
- A plugin/reflection framework: adds indirection before rule variety justifies it.
- Applying timestamp gaps to earthquakes: earthquake events are irregular and do not have a fixed sampling interval.
- Deliberate bad production rows: failure scenarios belong in compact local fixtures and tests.
