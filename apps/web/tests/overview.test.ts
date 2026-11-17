import assert from "node:assert/strict";
import test from "node:test";
import { DRIFT_UNAVAILABLE, type DriftResult } from "../lib/drift";
import { overviewEvidence } from "../lib/overview";

const date = "2026-11-17T00:00:00Z";
const driftResult: DriftResult = {
  id: 1,
  datasetSlug: "fixture",
  datasetName: "Synthetic dataset",
  columnName: "value",
  method: "PSI",
  status: "STABLE",
  severity: "INFO",
  baselineVersion: 1,
  observedMetric: 0.1,
  threshold: 0.2,
  baselineSampleCount: 100,
  currentSampleCount: 100,
  details: {},
  evaluatedAt: date,
};

test("failed evidence reads cannot produce successful zero counters", () => {
  const evidence = overviewEvidence(
    { incidents: [], message: "Incident data is unavailable." },
    { dataset: "all", results: [], message: DRIFT_UNAVAILABLE },
    { datasets: [], message: "Data quality is unavailable." },
  );
  assert.equal(evidence.incidentCount, "Unavailable");
  assert.equal(evidence.driftCount, "Unavailable");
  assert.equal(evidence.datasetCount, "Unavailable");
  assert.equal(evidence.incomplete, true);
  assert.equal(evidence.driftComplete, false);
});

test("absent or skipped drift is inconclusive even when incident reads succeed", () => {
  for (const results of [[], [{ ...driftResult, status: "SKIPPED" as const }]]) {
    const evidence = overviewEvidence({ incidents: [] }, { dataset: "all", results }, { datasets: [] });
    assert.equal(evidence.incidentCount, 0);
    assert.equal(evidence.driftCount, "Unknown");
    assert.equal(evidence.incomplete, true);
    assert.equal(evidence.driftComplete, false);
  }
});

test("mixed stable and skipped results distinguish a partial zero from a complete zero", () => {
  const incomplete = overviewEvidence(
    { incidents: [] },
    { dataset: "all", results: [driftResult, { ...driftResult, id: 2, status: "SKIPPED" }] },
    { datasets: [] },
  );
  const complete = overviewEvidence(
    { incidents: [] }, { dataset: "all", results: [driftResult] }, { datasets: [] },
  );
  assert.equal(incomplete.driftCount, 0);
  assert.equal(incomplete.incomplete, true);
  assert.deepEqual(incomplete.notes, ["Some drift checks were skipped."]);
  assert.equal(complete.driftCount, 0);
  assert.equal(complete.incomplete, false);
});

test("drift errors stay visible as signals alongside incomplete evaluation", () => {
  const evidence = overviewEvidence(
    { incidents: [] },
    { dataset: "all", results: [{ ...driftResult, status: "ERROR" }] },
    { datasets: [] },
  );
  assert.equal(evidence.driftCount, 1);
  assert.equal(evidence.driftSignals[0].status, "ERROR");
  assert.equal(evidence.incomplete, true);
  assert.ok(evidence.notes.includes("Some drift checks failed."));
});
