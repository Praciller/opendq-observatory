import { DRIFT_UNAVAILABLE, type DriftResponse } from "./drift";
import type { IncidentsResponse } from "./incidents";
import type { QualityResponse } from "./quality";

export function overviewEvidence(incidents: IncidentsResponse, drift: DriftResponse, quality: QualityResponse) {
  const activeIncidents = incidents.incidents.filter((incident) => incident.status !== "RESOLVED");
  const driftSignals = drift.results.filter((result) => ["DRIFT", "WARN", "ERROR"].includes(result.status));
  const driftEvaluated = drift.results.some((result) => result.status !== "SKIPPED" && result.status !== "ERROR");
  const skippedDrift = drift.results.some((result) => result.status === "SKIPPED");
  const failedDrift = driftSignals.some((result) => result.status === "ERROR");
  const driftComplete = driftEvaluated && !skippedDrift && !failedDrift;

  return {
    activeIncidents,
    driftSignals,
    incomplete: Boolean(incidents.message || !driftComplete),
    notes: [
      incidents.message,
      drift.message ?? (!driftEvaluated ? "No completed drift results were returned." : skippedDrift ? "Some drift checks were skipped." : null),
      failedDrift ? "Some drift checks failed." : null,
    ].filter(Boolean),
    incidentCount: incidents.message ? "Unavailable" : activeIncidents.length,
    driftCount: driftEvaluated || driftSignals.length > 0 ? driftSignals.length : drift.message === DRIFT_UNAVAILABLE ? "Unavailable" : "Unknown",
    datasetCount: quality.message ? "Unavailable" : quality.datasets.filter((dataset) => dataset.evaluationRunId !== null).length,
    driftComplete,
  };
}
