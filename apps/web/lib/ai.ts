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
  return {
    id: row.id,
    incidentId: row.incident_id,
    provider: row.provider,
    model: row.model,
    promptVersion: row.prompt_version,
    status: row.status,
    explanation: {
      summary: row.summary,
      probableCauseExplanation: row.probable_cause_explanation,
      evidenceHighlights: highlights,
      investigationSteps: strings(row.investigation_steps_json),
      uncertainties: strings(row.uncertainties_json),
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
      `SELECT id, incident_id, provider, model, prompt_version, status,
              summary, probable_cause_explanation, evidence_highlights_json,
              investigation_steps_json, uncertainties_json, latency_ms, input_size,
              output_size, provider_request_id, cache_hit, attempts_json,
              error_code, error_message, created_at
       FROM ai_incident_analyses
       WHERE incident_id = $1::uuid ORDER BY created_at DESC LIMIT 1`,
      [incidentId],
    );
    if (rows.length === 0) return { analysis: null, message: "No AI incident explanation is available." };
    return { analysis: mapAIAnalysisRow(rows[0]) };
  } catch {
    return { analysis: null, message: "AI analysis data is unavailable." };
  }
}
