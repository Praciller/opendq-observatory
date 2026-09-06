# Reliability SLIs and SLOs

OpenDQ separates execution reliability from the state of the data being evaluated. A successful pipeline run can legitimately produce a quality `FAIL` or a drift `DRIFT`; those outcomes are evidence about the data, not proof that the runtime failed.

## Measured window

The reliability surface measures the most recent 30 days of persisted history. The window is derived from `ingestion_runs.started_at`; an empty or incomplete history is reported as `INSUFFICIENT_HISTORY`, not converted into a percentage.

## Service-level indicators

| SLI | Evidence | Successful execution | Failure signal |
| --- | --- | --- | --- |
| Scheduled pipeline execution | `ingestion_runs` | `SUCCESS` or `NO_CHANGE` | `FAILED` or `PARTIAL` |
| Quality evaluation execution | `quality_evaluation_runs` | `SUCCESS` | `FAILED` |
| Drift evaluation execution | `drift_evaluation_runs` | `SUCCESS` or `PARTIAL` | `FAILED` or `NO_BASELINE` |
| Latest successful ingestion | `ingestion_runs.finished_at` | Latest `SUCCESS` timestamp | Missing/stale timestamp |
| Incident reconciliation | Persisted incident/event state | Incident state transition completes | Runtime error or missing reconciliation |
| Public API availability | Release-time `GET /api/health` | HTTP 200 with database healthy | Non-200 or degraded response |

## Objectives

- Scheduled pipeline execution: target at least 99% successful executions over a sufficiently long measured window. The current application does not claim this objective has been met unless the displayed history supports the calculation.
- Freshness: evaluate against each dataset's existing quality thresholds. Freshness failure is a data-quality outcome and is reported separately from pipeline execution.
- Public API: healthy during release validation; this is a point-in-time release gate, not a historical uptime claim.
- Incident reconciliation: completed evaluation runs should reconcile without runtime errors. Historical attainment is `INSUFFICIENT_HISTORY` until the required evidence is available.

## Interpretation rules

- `PASS`/`SUCCESS` means the persisted execution or evaluation completed according to its contract.
- `PARTIAL` means evaluation completed with bounded skips or mixed outcomes; it is not silently promoted to a clean pass.
- `FAIL`, `DRIFT`, and open incidents describe data or operational evidence and remain visible even when execution succeeded.
- No universal health score is calculated. Each state retains its domain meaning.
