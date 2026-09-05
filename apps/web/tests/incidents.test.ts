import assert from "node:assert/strict";
import test from "node:test";

import { incidentEmptyState, mapIncidentRow } from "../lib/incidents";
import { computeDownstreamImpact, lineageEmptyState } from "../lib/lineage";

test("incidents API has an honest empty state", () => {
  assert.deepEqual(incidentEmptyState(), { incidents: [], message: "No incidents detected." });
});

test("incident rows expose deterministic lifecycle evidence", () => {
  const incident = mapIncidentRow({
    id: "incident-1",
    incident_key: "hourly-weather:temperature-range",
    incident_kind: "DATA_QUALITY",
    dataset_slug: "hourly-weather",
    dataset_name: "Hourly weather",
    rule_slug: "temperature-range",
    rule_name: "Temperature validity range",
    status: "OPEN",
    severity: "HIGH",
    opened_at: new Date("2026-09-06T01:00:00Z"),
    last_seen_at: new Date("2026-09-06T02:00:00Z"),
    resolved_at: null,
    occurrence_count: 2,
    summary: "Temperature failed.",
    evidence_json: { observed: { invalid_records: 1 } },
  });

  assert.equal(incident.status, "OPEN");
  assert.equal(incident.occurrenceCount, 2);
  assert.deepEqual(incident.evidence, { observed: { invalid_records: 1 } });
});

test("lineage traversal returns shortest deterministic impact paths", () => {
  const impact = computeDownstreamImpact(
    [
      { key: "dataset:hourly-weather", name: "Weather", nodeType: "DATASET" },
      { key: "process:quality", name: "Quality", nodeType: "PROCESS" },
      { key: "api:quality", name: "API", nodeType: "API" },
    ],
    [
      { upstreamKey: "dataset:hourly-weather", downstreamKey: "process:quality", edgeType: "EVALUATED_BY" },
      { upstreamKey: "process:quality", downstreamKey: "api:quality", edgeType: "SERVED_BY" },
    ],
    "dataset:hourly-weather",
  );

  assert.deepEqual(impact.map((item) => [item.key, item.distance]), [
    ["process:quality", 1],
    ["api:quality", 2],
  ]);
});

test("lineage API has an honest empty state", () => {
  assert.deepEqual(lineageEmptyState("hourly-weather"), {
    dataset: "hourly-weather",
    nodes: [],
    edges: [],
    impact: [],
    message: "Lineage is unavailable.",
  });
});
