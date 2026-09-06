# Deterministic root-cause analysis

RCA is an evidence aggregation and ranking layer. It does not use an LLM, embeddings, a vector database, or generative explanations, and it does not claim calibrated causal probability.

## Evidence

The analyzer reads persisted quality results, drift results, ingestion status/errors, schema differences, and upstream lineage. Controlled causes are:

- `UPSTREAM_SOURCE_FAILURE`
- `SCHEMA_CHANGE`
- `FRESHNESS_DELAY`
- `TIMESTAMP_GAP`
- `INVALID_VALUES`
- `VOLUME_CHANGE`
- `DISTRIBUTION_SHIFT`
- `DATABASE_OR_PIPELINE_ERROR`
- `UNKNOWN`

Direct matching evidence has the strongest weight. Temporally aligned evidence and same-dataset evidence are included in the signal details; upstream source lineage can add context to a source-failure signal. Downstream assets are reported as affected impact, never promoted to a cause solely by reachability.

## Confidence and reproducibility

`deterministic-rca-v1` ranks summed weights in deterministic cause-name order for ties. `HIGH` requires a strong score with a lead over the runner-up, `MEDIUM` represents a useful but ambiguous signal, `LOW` is weak evidence, and `UNKNOWN` means no useful persisted signal. Every analysis stores a fingerprint, candidate scores, and `root_cause_evidence` rows with reason codes and source references. The fingerprint ignores database-generated row IDs when the semantic evidence is unchanged, avoiding duplicate identical RCA history.

## CLI and API

```powershell
python -m opendq rca analyze <incident-id>
python -m opendq rca show <incident-id>
python -m opendq rca list
```

The read-only API is `/api/incidents/<id>/rca`; incident detail renders probable cause, confidence, ranked candidates, supporting evidence, algorithm version, and affected assets. A healthy production deployment with zero incidents correctly has zero RCA executions.

The optional AI Incident Copilot consumes this persisted RCA and bounded
quality/drift/lineage/timeline evidence. It is not part of deterministic
ranking and cannot overwrite it. The AI explanation route is
`GET /api/incidents/<id>/ai`; inference is only run by the trusted CLI/workflow
and the deterministic fallback is persisted when providers are unavailable.
