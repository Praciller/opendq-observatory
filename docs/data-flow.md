# Evidence and data flow

```mermaid
flowchart LR
    Observation[Normalized observation] --> Rule[Quality rule result]
    Rule --> Drift[Drift result]
    Rule --> Incident[Incident state]
    Drift --> Incident
    Incident --> Evidence[Bounded evidence and timeline]
    Evidence --> Impact[Lineage impact snapshot]
    Evidence --> RCA[Deterministic RCA ranking]
    RCA --> Explanation[Optional AI explanation or deterministic fallback]
```

Each arrow is backed by persisted PostgreSQL records. Quality and drift results preserve their own status semantics; an execution can succeed while the data outcome is `FAIL` or `DRIFT`. RCA ranks evidence and is not causal proof. The optional AI layer receives public-only, bounded evidence and cannot alter the incident, quality, drift, or lineage state.
