import { queryValues } from "./db";

export type AIEvidenceHighlight = { evidenceId: string; text: string };

export type AIExplanation = {
  summary: string;
  probableCauseExplanation: string;
  evidenceHighlights: AIEvidenceHighlight[];
  investigationSteps: string[];
  uncertainties: string[];
};

export type AIAnalysis = {
  id: string;
  incidentId: string;
  provider: string;
  model: string;
  deterministicRcaAnalysisId: string | null;
  promptVersion: string;
  status: "SUCCESS" | "FALLBACK" | "FAILED" | "SKIPPED";
  explanation: AIExplanation;
  latencyMs: number;
  inputSize: number;
  outputSize: number;
  providerRequestId: string | null;
  cacheHit: boolean;
  attempts: Array<Record<string, unknown>>;
  errorCode: string | null;
  errorMessage: string | null;
  createdAt: string;
};

export type AIResponse = { analysis: AIAnalysis | null; message?: string };

function dateValue(value: Date | string): string {
  return new Date(value).toISOString();
}

export function mapAIAnalysisRow(row: {
  id: string;
  incident_id: string;
  provider: string;
  model: string;
  deterministic_rca_analysis_id?: string | null;
  rca_top_cause?: string | null;
  prompt_version: string;
  status: AIAnalysis["status"];
  summary: string;
  probable_cause_explanation: string;
  evidence_highlights_json: unknown;
  investigation_steps_json: unknown;
  uncertainties_json: unknown;
  latency_ms: number;
  input_size: number;
  output_size: number;
  provider_request_id: string | null;
  cache_hit: boolean;
  attempts_json: unknown;
  error_code: string | null;
  error_message: string | null;
  created_at: Date | string;
}): AIAnalysis {
  const highlights = Array.isArray(row.evidence_highlights_json)
    ? row.evidence_highlights_json
        .filter((item): item is { evidence_id: string; text: string } => {
          return Boolean(item && typeof item === "object" && "evidence_id" in item && "text" in item);
        })
        .map((item) => ({ evidenceId: item.evidence_id, text: item.text }))
    : [];
  const strings = (value: unknown): string[] =>
    Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
  const fallback = row.status === "FALLBACK";
  const legacyShift = row.rca_top_cause == null &&
    row.probable_cause_explanation === "This explanation follows the persisted deterministic RCA result. The leading cause is distribution shift; the AI provider was not used or was unavailable.";
  const driftFallback = fallback && (row.rca_top_cause === "DISTRIBUTION_SHIFT" || legacyShift);
  const savedExplanation = fallback
    ? row.probable_cause_explanation.replace(
      /^This explanation follows the persisted deterministic RCA result\. The leading cause is /,
      "This explanation follows the persisted deterministic RCA result. The leading rule-based signal is ",
    )
    : row.probable_cause_explanation;
  const uncertainties = strings(row.uncertainties_json);
  if (driftFallback && !uncertainties.includes("The cause of the distribution change remains unconfirmed.")) {
    uncertainties.push("The cause of the distribution change remains unconfirmed.");
  }
  return {
    id: row.id,
    incidentId: row.incident_id,
    provider: row.provider,
    model: row.model,
    deterministicRcaAnalysisId: row.deterministic_rca_analysis_id ?? null,
    promptVersion: row.prompt_version,
    status: row.status,
    explanation: {
      summary: driftFallback
        ? "A distribution shift was detected against the baseline."
        : fallback
          ? row.summary.replace(/ as the leading explanation with (?:high|medium|low|unknown) confidence\.$/, " as the leading rule-based signal.")
          : row.summary,
      probableCauseExplanation: driftFallback
        ? "PSI indicates a change in distribution but does not establish its underlying cause. The AI provider was not used or was unavailable."
        : savedExplanation,
      evidenceHighlights: highlights,
      investigationSteps: strings(row.investigation_steps_json),
      uncertainties,
    },
    latencyMs: Number(row.latency_ms),
    inputSize: Number(row.input_size),
    outputSize: Number(row.output_size),
    providerRequestId: row.provider_request_id,
    cacheHit: Boolean(row.cache_hit),
    attempts: Array.isArray(row.attempts_json)
      ? row.attempts_json.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
      : [],
    errorCode: row.error_code,
    errorMessage: row.error_message,
    createdAt: dateValue(row.created_at),
  };
}

export async function getAiAnalysis(incidentId: string): Promise<AIResponse> {
  if (!/^[0-9a-f-]{36}$/i.test(incidentId)) return { analysis: null, message: "AI analysis not found." };
  try {
    const rows = await queryValues<Parameters<typeof mapAIAnalysisRow>[0]>(
      `SELECT ai.id, ai.incident_id, ai.provider, ai.model, ai.prompt_version, ai.status,
              ai.summary, ai.probable_cause_explanation, ai.evidence_highlights_json,
              ai.investigation_steps_json, ai.uncertainties_json, ai.latency_ms, ai.input_size,
              ai.output_size, ai.provider_request_id, ai.cache_hit, ai.attempts_json,
              ai.error_code, ai.error_message, ai.created_at, rca.id AS deterministic_rca_analysis_id,
              rca.top_cause AS rca_top_cause
       FROM ai_incident_analyses ai
       LEFT JOIN root_cause_analyses rca ON rca.id = ai.deterministic_rca_analysis_id
                                     AND rca.incident_id = ai.incident_id
       WHERE ai.incident_id = $1::uuid ORDER BY ai.created_at DESC LIMIT 1`,
      [incidentId],
    );
    if (rows.length === 0) return { analysis: null, message: "No AI incident explanation is available." };
    return { analysis: mapAIAnalysisRow(rows[0]) };
  } catch {
    return { analysis: null, message: "AI analysis data is unavailable." };
  }
}
