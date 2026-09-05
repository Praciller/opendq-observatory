# ADR 0007: Persist incident lineage impact snapshots

## Decision

When an incident first opens, OpenDQ stores the current downstream lineage nodes, shortest distances, and paths in `incident_impacts`. Repeated observations do not overwrite that original snapshot.

## Rationale

Lineage is operational context that can change. Persisting the impact at incident open time makes historical blast-radius claims reviewable without reconstructing a graph that may no longer be identical.

## Consequences

The snapshot can become stale by design. The live lineage API remains available for current topology, while incident detail shows the captured historical impact. Traversal is deliberately bounded and provider-neutral.
