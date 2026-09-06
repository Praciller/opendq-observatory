import assert from "node:assert/strict";
import test from "node:test";

import { buildHealthResponse, sourceEmptyState } from "../lib/status";
import { qualityStatusFromCounts } from "../lib/quality";
import { driftEmptyState, mapDriftRow } from "../lib/drift";

test("health response is healthy only when database is reachable", async () => {
  assert.deepEqual(await buildHealthResponse(async () => true), {
    status: "healthy",
    database: "healthy",
  });
  assert.deepEqual(await buildHealthResponse(async () => false), {
    status: "degraded",
    database: "unavailable",
  });
});

test("source status has an honest pre-ingestion empty state", () => {
  assert.deepEqual(sourceEmptyState(), {
    sources: [],
    message: "No source ingestion has been recorded yet.",
  });
});

test("quality status separates pass, warning, fail, and unknown states", () => {
  assert.equal(qualityStatusFromCounts({ failed: 0, warned: 0, errored: 0, evaluated: 0, passed: 0 }), "UNKNOWN");
  assert.equal(qualityStatusFromCounts({ failed: 0, warned: 0, errored: 0, evaluated: 3, passed: 3 }), "PASS");
  assert.equal(qualityStatusFromCounts({ failed: 0, warned: 1, errored: 0, evaluated: 3, passed: 2 }), "WARN");
  assert.equal(qualityStatusFromCounts({ failed: 1, warned: 0, errored: 0, evaluated: 3, passed: 2 }), "FAIL");
  assert.equal(qualityStatusFromCounts({ failed: 0, warned: 0, errored: 1, evaluated: 3, passed: 2 }), "ERROR");
  assert.equal(qualityStatusFromCounts({ failed: 0, warned: 0, errored: 0, evaluated: 3, passed: 0 }), "UNKNOWN");
});

test("drift has an honest insufficient-baseline state", () => {
  assert.deepEqual(driftEmptyState("hourly-weather", "Insufficient baseline data."), {
    dataset: "hourly-weather",
    results: [],
    message: "Insufficient baseline data.",
  });
});

test("drift rows expose baseline and metric evidence", () => {
  const drift = mapDriftRow({
    id: 1,
    dataset_slug: "hourly-weather",
    dataset_name: "Hourly weather",
    column_name: "temperature_c",
    method: "PSI",
    status: "DRIFT",
    severity: "WARNING",
    baseline_version: 2,
    observed_metric: 0.42,
    threshold: 0.2,
    baseline_sample_count: 100,
    current_sample_count: 24,
    details_json: { epsilon: 0.000001 },
    evaluated_at: new Date("2026-09-06T02:00:00Z"),
  });

  assert.equal(drift.status, "DRIFT");
  assert.equal(drift.baselineVersion, 2);
  assert.equal(drift.observedMetric, 0.42);
  assert.deepEqual(drift.details, { epsilon: 0.000001 });
});

