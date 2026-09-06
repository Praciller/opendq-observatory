# Interview guide

## Why deterministic-first?

The pipeline must remain useful, explainable, and safe without an external model or paid provider. Explicit SQL, typed contracts, persisted evidence, and deterministic ranking make failures reproducible in CI and understandable in a review. AI is an optional explanation layer, never the source of operational truth.

## Design talking points

- **Idempotency:** PostgreSQL partial/conditional uniqueness protects logical observation identity and prevents duplicate active incidents.
- **Quality versus drift:** quality asks whether records satisfy contracts; drift asks whether a bounded distribution or schema changed. They can fail independently.
- **Incident state machine:** `OPEN`, `ACKNOWLEDGED`, and `RESOLVED` are persisted with event history. A passing evaluation resolves active state; a warning or skip does not silently resolve it.
- **Partial unique index:** one active incident per dataset/rule is enforced in the database, so concurrent evaluators cannot create duplicate active incidents.
- **Lineage snapshots:** new incidents capture downstream impact at detection time, preserving historical evidence even if the live graph changes.
- **PSI:** PSI is a compact, explainable distribution-shift signal for these small numeric windows; it is not universally ideal and is not causal discovery.
- **RCA boundary:** deterministic RCA ranks controlled hypotheses from evidence. It identifies a probable cause category; it does not prove causality.
- **AI boundary:** provider input is public-only and bounded, output is schema-validated and evidence-ID grounded, failures fall back deterministically, and GET requests never trigger inference.
- **Free-tier design:** batch processing, two public sources, one small PostgreSQL store, bounded windows, and optional cached AI avoid always-on infrastructure.
- **Future Kafka boundary:** if throughput or latency requires streaming later, Kafka would sit between source adapters and a durable ingestion consumer. It is not required for the current batch problem and would add operational cost and failure modes.

## Trade-offs to state plainly

The product is batch rather than streaming, covers a small public-source set, uses simple PSI, keeps PostgreSQL small, and treats external AI as optional/quota-bound. The local benchmark is a Windows fixture baseline, not a cross-hardware performance claim. Production history is still short, so some SLOs remain `INSUFFICIENT_HISTORY`.
