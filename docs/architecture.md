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
PostgreSQL observations + ingestion runs
    ↓
Deterministic quality rules
    ↓
PostgreSQL quality runs + results
    ↓
Web/API + quality dashboard
```

The source adapter owns transport and upstream parsing. Normalization converts source-specific fields into canonical Pydantic records with UTC timestamps. Persistence uses visible parameterized SQL and PostgreSQL constraints. The Next.js app reads persisted state; it does not fabricate metrics or duplicate the schema in an ORM.

Phase 1.5 uses scheduled micro-batches every six hours. Phase 2 evaluates persisted normalized observations after a successful or no-change ingestion. Ingestion health and data-quality health are separate: a successful ingestion can produce a quality FAIL, while a rule runtime ERROR is persisted without rewriting the ingestion result.

Quality results are deterministic, explainable, and persisted in PostgreSQL. The score is only a transparent summary of PASS/WARN/FAIL results; SKIPPED and ERROR results remain visible and are not silently treated as PASS. A future streaming source can be added at the adapter boundary if justified; Kafka/Redpanda are intentionally not required now.

