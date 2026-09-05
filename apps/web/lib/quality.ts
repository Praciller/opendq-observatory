import { query } from "./db";

export type QualityStatus = "PASS" | "WARN" | "FAIL" | "ERROR" | "UNKNOWN";

export type QualityResult = {
  ruleSlug: string;
  ruleName: string;
  dimension: string;
  severity: string;
  status: "PASS" | "WARN" | "FAIL" | "ERROR" | "SKIPPED";
  observedValue: Record<string, unknown>;
  expectedValue: Record<string, unknown>;
  affectedRecords: number;
  evaluatedRecords: number;
  details: Record<string, unknown>;
  evaluatedAt: string;
};

export type QualityDatasetSummary = {
  datasetSlug: string;
  datasetName: string;
  evaluationRunId: string | null;
  status: QualityStatus;
  score: number | null;
  evaluatedAt: string | null;
  ruleCounts: {
    evaluated: number;
    passed: number;
    warned: number;
    failed: number;
    errored: number;
    skipped: number;
  };
  results: QualityResult[];
};

export type QualityResponse = {
  datasets: QualityDatasetSummary[];
  message?: string;
};

export function qualityStatusFromCounts(counts: {
  failed: number;
  warned: number;
  errored: number;
  evaluated: number;
  passed: number;
}): QualityStatus {
  if (counts.evaluated === 0) return "UNKNOWN";
  if (counts.errored > 0) return "ERROR";
  if (counts.failed > 0) return "FAIL";
  if (counts.warned > 0) return "WARN";
  if (counts.passed === 0) return "UNKNOWN";
  return "PASS";
}

type QualityRow = {
  dataset_slug: string;
  dataset_name: string;
  evaluation_run_id: string | null;
  score: number | null;
  evaluated_at: Date | null;
  rules_evaluated: number | null;
  rules_passed: number | null;
  rules_warned: number | null;
  rules_failed: number | null;
  rules_errored: number | null;
  rules_skipped: number | null;
  results: Array<{
    rule_slug: string;
    rule_name: string;
    dimension: string;
    severity: string;
    status: QualityResult["status"];
    observed_value: Record<string, unknown>;
    expected_value: Record<string, unknown>;
    affected_records: number;
    evaluated_records: number;
    details: Record<string, unknown>;
    evaluated_at: Date;
  }>;
};

export async function getQualitySummaries(): Promise<QualityResponse> {
  try {
    const rows = await query<QualityRow>(
      `WITH latest AS (
         SELECT qer.*,
                row_number() OVER (PARTITION BY dataset_id ORDER BY started_at DESC) AS row_number
         FROM quality_evaluation_runs qer
       )
       SELECT d.slug AS dataset_slug,
              d.name AS dataset_name,
              latest.evaluation_run_id,
              latest.score,
              latest.finished_at AS evaluated_at,
              latest.rules_evaluated,
              latest.rules_passed,
              latest.rules_warned,
              latest.rules_failed,
              latest.rules_errored,
              latest.rules_skipped,
              coalesce(
                jsonb_agg(
                  jsonb_build_object(
                    'rule_slug', qr.slug,
                    'rule_name', qr.name,
                    'dimension', qr.dimension,
                    'severity', qr.severity,
                    'status', result.status,
                    'observed_value', result.observed_value,
                    'expected_value', result.expected_value,
                    'affected_records', result.affected_records,
                    'evaluated_records', result.evaluated_records,
                    'details', result.details_json,
                    'evaluated_at', result.evaluated_at
                  ) ORDER BY result.id
                ) FILTER (WHERE result.id IS NOT NULL),
                '[]'::jsonb
              ) AS results
       FROM datasets d
       LEFT JOIN latest ON latest.dataset_id = d.id AND latest.row_number = 1
       LEFT JOIN quality_results result ON result.evaluation_run_id = latest.evaluation_run_id
       LEFT JOIN quality_rules qr ON qr.id = result.rule_id
       GROUP BY d.id, d.slug, d.name, latest.evaluation_run_id, latest.score,
                latest.finished_at, latest.rules_evaluated, latest.rules_passed,
                latest.rules_warned, latest.rules_failed, latest.rules_errored,
                latest.rules_skipped
       ORDER BY d.id`,
    );
    return {
      datasets: rows.map((row) => {
        const counts = {
          evaluated: row.rules_evaluated ?? 0,
          passed: row.rules_passed ?? 0,
          warned: row.rules_warned ?? 0,
          failed: row.rules_failed ?? 0,
          errored: row.rules_errored ?? 0,
          skipped: row.rules_skipped ?? 0,
        };
        return {
          datasetSlug: row.dataset_slug,
          datasetName: row.dataset_name,
          evaluationRunId: row.evaluation_run_id,
        status: qualityStatusFromCounts(counts),
          score: row.score,
          evaluatedAt: row.evaluated_at?.toISOString() ?? null,
          ruleCounts: counts,
          results: (row.results ?? []).map((result) => ({
            ruleSlug: result.rule_slug,
            ruleName: result.rule_name,
            dimension: result.dimension,
            severity: result.severity,
            status: result.status,
            observedValue: result.observed_value,
            expectedValue: result.expected_value,
            affectedRecords: result.affected_records,
            evaluatedRecords: result.evaluated_records,
            details: result.details,
            evaluatedAt: new Date(result.evaluated_at).toISOString(),
          })),
        };
      }),
    };
  } catch {
    return { datasets: [], message: "Data quality is unavailable." };
  }
}
