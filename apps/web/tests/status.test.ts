import assert from "node:assert/strict";
import test from "node:test";

import { buildHealthResponse, sourceEmptyState } from "../lib/status";

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

