import assert from "node:assert/strict";
import test from "node:test";

import {
  evaluatePollReadiness,
  MAX_SOURCE_POLL_AGE_HOURS,
} from "../lib/source-freshness";
import type { SourceStatus } from "../lib/status";

const now = new Date("2026-10-22T12:00:00Z");

function source(
  lastSuccessfulIngestion: string | null,
  enabled = true,
): SourceStatus {
  return {
    slug: "open-meteo",
    name: "Open-Meteo",
    enabled,
    hasIngestion: lastSuccessfulIngestion !== null,
    lastSuccessfulIngestion,
  };
}

test("healthy recency uses the last successful poll, not a dataset event timestamp", () => {
  const summary = evaluatePollReadiness(
    { sources: [source("2026-10-22T06:00:00Z")] },
    true,
    now,
  );
  assert.equal(summary.status, "healthy");
  assert.equal(summary.sources[0].state, "CURRENT");
  assert.equal(summary.sources[0].ageHours, 6);
  assert.equal(summary.maxPollAgeHours, MAX_SOURCE_POLL_AGE_HOURS);
});

test("stale poll degrades health even when database connectivity works", () => {
  const summary = evaluatePollReadiness(
    { sources: [source("2026-10-21T12:00:00Z")] },
    true,
    now,
  );
  assert.equal(summary.status, "degraded");
  assert.equal(summary.sources[0].state, "STALE");
});

test("unknown history and invalid timestamps never count as healthy", () => {
  for (const timestamp of [null, "not-a-date", "2026-10-23T00:00:00Z"]) {
    const summary = evaluatePollReadiness({ sources: [source(timestamp)] }, true, now);
    assert.equal(summary.status, "degraded");
    assert.ok(["NO_HISTORY", "INVALID_TIME"].includes(summary.sources[0].state));
  }
});

test("disabled sources are excluded from enabled-source readiness", () => {
  const summary = evaluatePollReadiness(
    { sources: [source(null, false), { ...source("2026-10-22T11:00:00Z"), slug: "usgs" }] },
    true,
    now,
  );
  assert.equal(summary.status, "healthy");
  assert.equal(summary.sources[0].state, "DISABLED");
});

test("no registered sources or unavailable database cannot report healthy", () => {
  assert.equal(evaluatePollReadiness({ sources: [] }, true, now).status, "degraded");
  assert.equal(evaluatePollReadiness({ sources: [] }, false, now).status, "unavailable");
  assert.equal(
    evaluatePollReadiness({ sources: [], message: "Source status is unavailable." }, true, now)
      .status,
    "unavailable",
  );
});
