# ADR 0006: One active incident per dataset and rule

## Decision

OpenDQ keeps one active incident per dataset/rule pair. PostgreSQL enforces this with a partial unique index over `OPEN` and `ACKNOWLEDGED` rows. Resolved rows remain historical and permit a later failure to create a new incident.

## Rationale

This prevents six-hour scheduled runs from creating duplicate unresolved incidents while preserving occurrence counts and event history. The database constraint remains authoritative under concurrent reconciliation.

## Consequences

Cross-rule correlation and AI root-cause analysis are deferred. An ERROR observed while another active incident exists for the same rule follows the same logical key and does not create a second active row.
