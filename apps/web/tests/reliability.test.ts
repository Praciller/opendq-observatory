import assert from "node:assert/strict";
import test from "node:test";

import {
  mapReliabilityRow,
  reliabilityEmptyState,
  type ReliabilityRow,
} from "../lib/reliability";

test("reliability maps measured execution evidence without turning data outcomes into uptime", () => {
  const summary = mapReliabilityRow({
    window_start: new Date("2026-09-01T00:00:00Z"),
    window_end: new Date("2026-09-06T00:00:00Z"),
    pipeline_runs: 10,
    pipeline_successes: 9,
    pipeline_failures: 1,
    latest_pipeline_run_at: new Date("2026-09-06T00:00:00Z"),
    latest_successful_ingestion_at: new Date("2026-09-06T00:00:00Z"),
    quality_runs: 10,
    quality_successes: 10,
    quality_failures: 0,
    latest_quality_status: "SUCCESS",
    latest_quality_run_at: new Date("2026-09-06T00:00:00Z"),
    drift_runs: 10,
    drift_successes: 10,
    drift_failures: 0,
    latest_drift_status: "PARTIAL",
    latest_drift_run_at: new Date("2026-09-06T00:00:00Z"),
    open_incidents: 2,
    acknowledged_incidents: 0,
    resolved_incidents: 4,
  } satisfies ReliabilityRow);

  assert.equal(summary.window.state, "MEASURED");
  assert.equal(summary.execution.pipeline.successRate, 90);
  assert.equal(summary.execution.pipeline.failedExecutions, 1);
  assert.equal(summary.execution.quality.failedExecutions, 0);
  assert.equal(summary.state.quality, "SUCCESS");
  assert.equal(summary.state.drift, "PARTIAL");
  assert.equal(summary.incidents.open, 2);
});

test("reliability reports insufficient history instead of inventing an SLO percentage", () => {
  const summary = mapReliabilityRow({
    window_start: null,
    window_end: null,
    pipeline_runs: 0,
    pipeline_successes: 0,
    pipeline_failures: 0,
    latest_pipeline_run_at: null,
    latest_successful_ingestion_at: null,
    quality_runs: 0,
    quality_successes: 0,
    quality_failures: 0,
    latest_quality_status: null,
    latest_quality_run_at: null,
    drift_runs: 0,
    drift_successes: 0,
    drift_failures: 0,
    latest_drift_status: null,
    latest_drift_run_at: null,
    open_incidents: 0,
    acknowledged_incidents: 0,
    resolved_incidents: 0,
  } satisfies ReliabilityRow);

  assert.deepEqual(summary.window, { start: null, end: null, state: "INSUFFICIENT_HISTORY" });
  assert.equal(summary.execution.pipeline.successRate, null);
  assert.equal(summary.state.quality, "UNAVAILABLE");
  assert.equal(summary.state.drift, "UNAVAILABLE");
});

test("reliability has an honest unavailable state", () => {
  assert.deepEqual(reliabilityEmptyState(), {
    window: { start: null, end: null, state: "INSUFFICIENT_HISTORY" },
    execution: {
      pipeline: { runCount: 0, successfulExecutions: 0, failedExecutions: 0, successRate: null, latestRunAt: null, latestSuccessfulIngestionAt: null },
      quality: { runCount: 0, successfulExecutions: 0, failedExecutions: 0, successRate: null, latestRunAt: null },
      drift: { runCount: 0, successfulExecutions: 0, failedExecutions: 0, successRate: null, latestRunAt: null },
    },
    state: { quality: "UNAVAILABLE", drift: "UNAVAILABLE" },
    incidents: { open: 0, acknowledged: 0, resolved: 0 },
    message: "Reliability data is unavailable.",
  });
});
