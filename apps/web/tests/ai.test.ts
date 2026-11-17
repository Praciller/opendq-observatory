import assert from "node:assert/strict";
import test from "node:test";

import { mapAIAnalysisRow } from "../lib/ai";
import { readRcaSummary } from "../lib/rca";

function savedRow(overrides: Partial<Parameters<typeof mapAIAnalysisRow>[0]> = {}) {
  return {
    id: "analysis-1",
    incident_id: "incident-1",
    provider: "deterministic-fallback",
    model: "deterministic-rca-v1",
    prompt_version: "incident-copilot-v1",
    status: "FALLBACK" as const,
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
    ...overrides,
  };
}

test("AI analysis mapping preserves persisted fallback metadata", () => {
  const analysis = mapAIAnalysisRow(savedRow());

  assert.equal(analysis.status, "FALLBACK");
  assert.equal(analysis.explanation.evidenceHighlights[0].evidenceId, "drift-result:1");
  assert.equal(analysis.model, "deterministic-rca-v1");
});

test("legacy PSI language is qualified without changing RCA evidence text", () => {
  const old = "Probable cause: distribution shift. Evidence: psi distribution shift. Confidence: HIGH. Affected downstream assets: 1.";
  const normalized = readRcaSummary(old);
  assert.match(normalized, /PSI does not establish the underlying cause/);
  assert.match(normalized, /Evidence: psi distribution shift/);
  assert.doesNotMatch(normalized, /Probable cause|Confidence/);
  assert.equal(readRcaSummary(normalized), normalized);
});

test("cached deterministic drift fallback qualifies PSI and retains stored references", () => {
  const row = savedRow({
    rca_top_cause: "DISTRIBUTION_SHIFT",
    deterministic_rca_analysis_id: "older-rca",
    cache_hit: true,
    probable_cause_explanation: "Previous fixture copy.",
  });
  const analysis = mapAIAnalysisRow(row);
  assert.equal(analysis.status, "FALLBACK");
  assert.equal(analysis.cacheHit, true);
  assert.equal(analysis.deterministicRcaAnalysisId, "older-rca");
  assert.match(analysis.explanation.probableCauseExplanation, /does not establish/);
  assert.equal(analysis.explanation.evidenceHighlights[0].evidenceId, "drift-result:1");
  assert.equal(row.probable_cause_explanation, "Previous fixture copy.");
});

test("historic deterministic drift fallback with a deleted RCA stays unconfirmed", () => {
  const analysis = mapAIAnalysisRow(savedRow({
    deterministic_rca_analysis_id: null,
    probable_cause_explanation: "This explanation follows the persisted deterministic RCA result. The leading cause is distribution shift; the AI provider was not used or was unavailable.",
  }));
  assert.equal(analysis.deterministicRcaAnalysisId, null);
  assert.match(analysis.explanation.probableCauseExplanation, /does not establish/);
  assert.equal(analysis.status, "FALLBACK");
});

test("provider hypothesis stays byte-for-byte intact with its linked RCA snapshot", () => {
  const row = savedRow({
    status: "SUCCESS",
    provider: "synthetic-provider",
    rca_top_cause: "DISTRIBUTION_SHIFT",
    deterministic_rca_analysis_id: "older-rca",
    summary: "Saved provider hypothesis.",
    probable_cause_explanation: "Inspect the source sampling before attributing the shift.",
    uncertainties_json: ["Provider uncertainty."],
  });
  const analysis = mapAIAnalysisRow(row);
  assert.equal(analysis.deterministicRcaAnalysisId, "older-rca");
  assert.equal(analysis.explanation.summary, row.summary);
  assert.equal(analysis.explanation.probableCauseExplanation, row.probable_cause_explanation);
  assert.deepEqual(analysis.explanation.uncertainties, row.uncertainties_json);
});

test("invalid UUIDs return an honest empty state without database access", async () => {
  const { getAiAnalysis } = await import("../lib/ai");
  assert.deepEqual(await getAiAnalysis("not-a-uuid"), {
    analysis: null,
    message: "AI analysis not found.",
  });
});
