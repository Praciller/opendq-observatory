# ADR 0008: Use immutable versioned drift baselines

## Decision

Store compact numeric, categorical, and schema baselines in `drift_baselines`. Creating a new baseline creates the next version and deactivates the previous active version. Evaluations retain their baseline ID and version.

## Rationale

Silent baseline mutation makes historical drift claims unreproducible. Versioning also makes insufficient data explicit and keeps the free-tier runtime bounded: evaluations use a fixed latest observation window and compact distributions instead of replaying full history.

## Consequences

Operators must deliberately create or accept a new baseline. Production can honestly return `INSUFFICIENT_DATA` without being tuned to appear stable. Baseline rows never contain full raw datasets.
