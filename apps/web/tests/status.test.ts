import assert from "node:assert/strict";
import test from "node:test";

import { buildHealthResponse, sourceEmptyState } from "../lib/status";
import { qualityStatusFromCounts } from "../lib/quality";

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

