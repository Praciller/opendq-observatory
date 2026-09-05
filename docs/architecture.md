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
Deterministic incident reconciliation
    ↓
Lineage traversal + impact snapshot
    ↓
Read-only incident/lineage API + dashboard
```

The source adapter owns transport and upstream parsing. Normalization converts source-specific fields into canonical Pydantic records with UTC timestamps. Persistence uses visible parameterized SQL and PostgreSQL constraints. The Next.js app reads persisted state; it does not fabricate metrics or duplicate the schema in an ORM.

Phase 1.5 uses scheduled micro-batches every six hours. Phase 2 evaluates persisted normalized observations after a successful or no-change ingestion. Ingestion health and data-quality health are separate: a successful ingestion can produce a quality FAIL, while a rule runtime ERROR is persisted without rewriting the ingestion result.

Quality results are deterministic, explainable, and persisted in PostgreSQL. The score is only a transparent summary of PASS/WARN/FAIL results; SKIPPED and ERROR results remain visible and are not silently treated as PASS. A future streaming source can be added at the adapter boundary if justified; Kafka/Redpanda are intentionally not required now.

Phase 3 consumes persisted quality results without reimplementing quality logic. FAIL opens or updates one active DATA_QUALITY incident per dataset/rule; ERROR opens or updates an EVALUATION_ERROR incident; PASS resolves an active incident; WARN and SKIPPED do not change incident state. Lineage is a small provider-neutral graph seeded from real implemented sources, datasets, quality processes, APIs, and dashboard surfaces. New incidents capture a bounded downstream blast-radius snapshot so historical impact remains explainable if the graph changes later.

