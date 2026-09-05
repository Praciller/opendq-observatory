# ADR 0002: Batch before streaming

## Context

The first sources provide bounded public snapshots and the project has no Phase 1 need for continuous event transport.

## Decision

Use six-hour scheduled micro-batches and defer Kafka/Redpanda until a measured requirement exists.

## Consequences

The system is simpler to run and test on free tiers. A future streaming adapter will need to preserve the canonical contract and idempotency boundaries.

## Alternatives

Kafka, Redpanda, Airflow, and always-on queues were rejected as premature infrastructure.

