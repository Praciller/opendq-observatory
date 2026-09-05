# Architecture

```text
Public API
    ↓
Source Adapter
    ↓
Normalization
    ↓
Data Contract
    ↓
PostgreSQL
    ↓
Web/API
```

The source adapter owns transport and upstream parsing. Normalization converts source-specific fields into canonical Pydantic records with UTC timestamps. Persistence uses visible parameterized SQL and PostgreSQL constraints. The Next.js app reads persisted state; it does not fabricate metrics or duplicate the schema in an ORM.

Phase 0–1 uses scheduled micro-batches every six hours. Both selected sources publish bounded snapshots/feeds, and six-hour cadence preserves free-tier efficiency without an always-on worker. A future streaming source can be added at the adapter boundary and run locally with Kafka/Redpanda if justified; those services are intentionally not required now.

