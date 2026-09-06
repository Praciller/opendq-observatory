import assert from "node:assert/strict";
import test from "node:test";

import { mapAIAnalysisRow } from "../lib/ai";

test("AI analysis mapping preserves persisted provider explanation metadata", () => {
  const analysis = mapAIAnalysisRow({
    id: "analysis-1",
    incident_id: "incident-1",
    provider: "deterministic-fallback",
    model: "deterministic-rca-v1",
    prompt_version: "incident-copilot-v1",
    status: "FALLBACK",
    summary: "Deterministic explanation.",
    probable_cause_explanation: "The persisted RCA is authoritative.",
    evidence_highlights_json: [{ evidence_id: "drift-result:1", text: "PSI evidence." }],
    investigation_steps_json: ["Inspect the source window."],
    uncertainties_json: [],
    latency_ms: 0,
    input_size: 100,
    output_size: 200,
    provider_request_id: null,
    cache_hit: false,
    attempts_json: [],
    error_code: "AI_DISABLED",
    error_message: "Fallback used.",
    created_at: new Date("2026-09-06T01:00:00Z"),
  });

  assert.equal(analysis.status, "FALLBACK");
  assert.equal(analysis.explanation.evidenceHighlights[0].evidenceId, "drift-result:1");
  assert.equal(analysis.model, "deterministic-rca-v1");
});

test("invalid UUIDs return an honest empty state without database access", async () => {
  const { getAiAnalysis } = await import("../lib/ai");
  assert.deepEqual(await getAiAnalysis("not-a-uuid"), {
    analysis: null,
    message: "AI analysis not found.",
  });
});
