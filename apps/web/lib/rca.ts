import { queryValues } from "./db";

export type RCAEvidence = {
  evidenceType: string;
  sourceTable: string;
  sourceId: string | null;
  reasonCode: string;
  weight: number;
  details: Record<string, unknown>;
};

export type RCAAnalysis = {
  id: string;
  incidentId: string;
  status: string;
  topCause: string;
  confidence: string;
  algorithmVersion: string;
  evidenceFingerprint: string;
  summary: string;
  details: Record<string, unknown>;
  createdAt: string;
  evidence: RCAEvidence[];
};

export type RCAResponse = { analysis: RCAAnalysis | null; message?: string };

function dateValue(value: Date | string): string {
  return new Date(value).toISOString();
}

export async function getRca(incidentId: string): Promise<RCAResponse> {
  if (!/^[0-9a-f-]{36}$/i.test(incidentId)) return { analysis: null, message: "RCA analysis not found." };
  try {
    const rows = await queryValues<{
      id: string; incident_id: string; status: string; top_cause: string; confidence: string;
      algorithm_version: string; evidence_fingerprint: string; summary: string;
      details_json: Record<string, unknown>; created_at: Date;
    }>(
      `SELECT id, incident_id, status, top_cause, confidence, algorithm_version,
              evidence_fingerprint, summary, details_json, created_at
       FROM root_cause_analyses
       WHERE incident_id = $1::uuid ORDER BY created_at DESC LIMIT 1`,
      [incidentId],
    );
    if (rows.length === 0) return { analysis: null, message: "No RCA analysis is available." };
    const evidence = await queryValues<{
      evidence_type: string; source_table: string; source_id: string | null;
      reason_code: string; weight: number; details_json: Record<string, unknown>;
    }>(
      `SELECT evidence_type, source_table, source_id, reason_code, weight, details_json
       FROM root_cause_evidence WHERE analysis_id = $1::uuid ORDER BY weight DESC, id`,
      [rows[0].id],
    );
    const row = rows[0];
    return {
      analysis: {
        id: row.id,
        incidentId: row.incident_id,
        status: row.status,
        topCause: row.top_cause,
        confidence: row.confidence,
        algorithmVersion: row.algorithm_version,
        evidenceFingerprint: row.evidence_fingerprint,
        summary: row.summary,
        details: row.details_json,
        createdAt: dateValue(row.created_at),
        evidence: evidence.map((item) => ({
          evidenceType: item.evidence_type,
          sourceTable: item.source_table,
          sourceId: item.source_id,
          reasonCode: item.reason_code,
          weight: item.weight,
          details: item.details_json,
        })),
      },
    };
  } catch {
    return { analysis: null, message: "RCA data is unavailable." };
  }
}
