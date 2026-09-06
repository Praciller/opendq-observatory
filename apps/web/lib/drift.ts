import { queryValues } from "./db";

export type DriftStatus = "STABLE" | "WARN" | "DRIFT" | "ERROR" | "SKIPPED";
export type DriftResult = {
  id: number;
  datasetSlug: string;
  datasetName: string;
  columnName: string;
  method: string;
  status: DriftStatus;
  severity: string;
  baselineVersion: number | null;
  observedMetric: number | null;
  threshold: number | null;
  baselineSampleCount: number;
  currentSampleCount: number;
  details: Record<string, unknown>;
  evaluatedAt: string;
};

export type DriftResponse = { dataset: string; results: DriftResult[]; message?: string };

type DriftRow = {
  id: number;
  dataset_slug: string;
  dataset_name: string;
  column_name: string;
  method: string;
  status: DriftStatus;
  severity: string;
  baseline_version: number | null;
  observed_metric: number | null;
  threshold: number | null;
  baseline_sample_count: number;
  current_sample_count: number;
  details_json: Record<string, unknown>;
  evaluated_at: Date;
};

function normalizeDataset(dataset: string): string {
  return { "open-meteo": "hourly-weather", usgs: "earthquake-events", "usgs-earthquakes": "earthquake-events" }[dataset] ?? dataset;
}

function dateValue(value: Date | string): string {
  return new Date(value).toISOString();
}

export function driftEmptyState(dataset: string, message = "No drift evaluation has been recorded yet."): DriftResponse {
  return { dataset, results: [], message };
}

export function mapDriftRow(row: DriftRow): DriftResult {
  return {
    id: row.id,
    datasetSlug: row.dataset_slug,
    datasetName: row.dataset_name,
    columnName: row.column_name,
    method: row.method,
    status: row.status,
    severity: row.severity,
    baselineVersion: row.baseline_version,
    observedMetric: row.observed_metric,
    threshold: row.threshold,
    baselineSampleCount: row.baseline_sample_count,
    currentSampleCount: row.current_sample_count,
    details: row.details_json,
    evaluatedAt: dateValue(row.evaluated_at),
  };
}

export async function getDrift(dataset?: string): Promise<DriftResponse> {
  const normalized = dataset ? normalizeDataset(dataset) : "all";
  try {
    const rows = await queryValues<DriftRow>(
      `SELECT DISTINCT ON (d.slug, result.column_name, result.method)
              result.id, d.slug AS dataset_slug, d.name AS dataset_name,
              result.column_name, result.method, result.status, result.severity,
              result.baseline_version, result.observed_metric, result.threshold,
              result.baseline_sample_count, result.current_sample_count,
              result.details_json, result.evaluated_at
       FROM drift_results result
       JOIN datasets d ON d.id = result.dataset_id
       WHERE ($1 = 'all' OR d.slug = $1)
       ORDER BY d.slug, result.column_name, result.method, result.evaluated_at DESC`,
      [normalized],
    );
    if (rows.length > 0) {
      return { dataset: normalized, results: rows.map(mapDriftRow) };
    }
    const runs = await queryValues<{ status: string }>(
      `SELECT status FROM drift_evaluation_runs run
       JOIN datasets d ON d.id = run.dataset_id
       WHERE ($1 = 'all' OR d.slug = $1)
       ORDER BY run.started_at DESC LIMIT 1`,
      [normalized],
    );
    return driftEmptyState(
      normalized,
      runs[0]?.status === "NO_BASELINE" ? "Insufficient baseline data." : "No drift evaluation has been recorded yet.",
    );
  } catch {
    return driftEmptyState(normalized, "Drift data is unavailable.");
  }
}
