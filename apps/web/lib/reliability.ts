import { query } from "./db";

export type ReliabilityState = "SUCCESS" | "PARTIAL" | "FAILED" | "NO_BASELINE" | "UNAVAILABLE";
export type ReliabilityWindowState = "MEASURED" | "INSUFFICIENT_HISTORY";

export type ReliabilityExecution = {
  runCount: number;
  successfulExecutions: number;
  failedExecutions: number;
  successRate: number | null;
  latestRunAt: string | null;
  latestSuccessfulIngestionAt?: string | null;
};

export type ReliabilitySummary = {
  window: { start: string | null; end: string | null; state: ReliabilityWindowState };
  execution: {
    pipeline: ReliabilityExecution & { latestSuccessfulIngestionAt: string | null };
    quality: ReliabilityExecution;
    drift: ReliabilityExecution;
  };
  state: { quality: ReliabilityState; drift: ReliabilityState };
  incidents: { open: number; acknowledged: number; resolved: number };
  message?: string;
};

export type ReliabilityRow = {
  window_start: Date | null;
  window_end: Date | null;
  pipeline_runs: number;
  pipeline_successes: number;
  pipeline_failures: number;
  latest_pipeline_run_at: Date | null;
  latest_successful_ingestion_at: Date | null;
  quality_runs: number;
  quality_successes: number;
  quality_failures: number;
  latest_quality_status: ReliabilityState | null;
  latest_quality_run_at: Date | null;
  drift_runs: number;
  drift_successes: number;
  drift_failures: number;
  latest_drift_status: ReliabilityState | null;
  latest_drift_run_at: Date | null;
  open_incidents: number;
  acknowledged_incidents: number;
  resolved_incidents: number;
};

function dateValue(value: Date | string | null): string | null {
  return value ? new Date(value).toISOString() : null;
}

function countValue(value: number | string | null): number {
  return Number(value ?? 0);
}

function execution(
  runs: number | string,
  successes: number | string,
  failures: number | string,
  latestRunAt: Date | null,
): ReliabilityExecution {
  const runCount = countValue(runs);
  const successfulExecutions = countValue(successes);
  return {
    runCount,
    successfulExecutions,
    failedExecutions: countValue(failures),
    successRate: runCount === 0 ? null : Math.round((successfulExecutions / runCount) * 10000) / 100,
    latestRunAt: dateValue(latestRunAt),
  };
}

export function mapReliabilityRow(row: ReliabilityRow): ReliabilitySummary {
  const pipeline = execution(
    row.pipeline_runs,
    row.pipeline_successes,
    row.pipeline_failures,
    row.latest_pipeline_run_at,
  );
  const quality = execution(
    row.quality_runs,
    row.quality_successes,
    row.quality_failures,
    row.latest_quality_run_at,
  );
  const drift = execution(
    row.drift_runs,
    row.drift_successes,
    row.drift_failures,
    row.latest_drift_run_at,
  );
  return {
    window: {
      start: dateValue(row.window_start),
      end: dateValue(row.window_end),
      state: row.pipeline_runs === 0 ? "INSUFFICIENT_HISTORY" : "MEASURED",
    },
    execution: {
      pipeline: { ...pipeline, latestSuccessfulIngestionAt: dateValue(row.latest_successful_ingestion_at) },
      quality,
      drift,
    },
    state: {
      quality: row.latest_quality_status ?? "UNAVAILABLE",
      drift: row.latest_drift_status ?? "UNAVAILABLE",
    },
    incidents: {
      open: countValue(row.open_incidents),
      acknowledged: countValue(row.acknowledged_incidents),
      resolved: countValue(row.resolved_incidents),
    },
  };
}

export function reliabilityEmptyState(): ReliabilitySummary {
  return {
    window: { start: null, end: null, state: "INSUFFICIENT_HISTORY" },
    execution: {
      pipeline: {
        runCount: 0,
        successfulExecutions: 0,
        failedExecutions: 0,
        successRate: null,
        latestRunAt: null,
        latestSuccessfulIngestionAt: null,
      },
      quality: { runCount: 0, successfulExecutions: 0, failedExecutions: 0, successRate: null, latestRunAt: null },
      drift: { runCount: 0, successfulExecutions: 0, failedExecutions: 0, successRate: null, latestRunAt: null },
    },
    state: { quality: "UNAVAILABLE", drift: "UNAVAILABLE" },
    incidents: { open: 0, acknowledged: 0, resolved: 0 },
    message: "Reliability data is unavailable.",
  };
}

export async function getReliability(): Promise<ReliabilitySummary> {
  try {
    const rows = await query<ReliabilityRow>(
      `WITH bounds AS (
         SELECT min(started_at) AS window_start, max(coalesce(finished_at, started_at)) AS window_end
         FROM ingestion_runs
         WHERE started_at >= now() - interval '30 days'
       ),
       pipeline AS (
         SELECT count(*) AS runs,
                count(*) FILTER (WHERE status IN ('SUCCESS', 'NO_CHANGE')) AS successes,
                count(*) FILTER (WHERE status IN ('FAILED', 'PARTIAL')) AS failures,
                max(finished_at) AS latest_run_at,
                max(finished_at) FILTER (WHERE status = 'SUCCESS') AS latest_successful_ingestion_at
         FROM ingestion_runs
         WHERE started_at >= now() - interval '30 days'
       ),
       quality AS (
         SELECT count(*) AS runs,
                count(*) FILTER (WHERE status = 'SUCCESS') AS successes,
                count(*) FILTER (WHERE status = 'FAILED') AS failures,
                max(finished_at) AS latest_run_at
         FROM quality_evaluation_runs
         WHERE started_at >= now() - interval '30 days'
       ),
       latest_quality AS (
         SELECT CASE WHEN rules_errored > 0 THEN 'FAILED'
                     WHEN rules_failed > 0 THEN 'PARTIAL'
                     WHEN rules_warned > 0 THEN 'PARTIAL'
                     ELSE status END AS status,
                finished_at
         FROM quality_evaluation_runs
         ORDER BY started_at DESC LIMIT 1
       ),
       drift AS (
         SELECT count(*) AS runs,
                count(*) FILTER (WHERE status IN ('SUCCESS', 'PARTIAL')) AS successes,
                count(*) FILTER (WHERE status IN ('FAILED', 'NO_BASELINE')) AS failures,
                max(finished_at) AS latest_run_at
         FROM drift_evaluation_runs
         WHERE started_at >= now() - interval '30 days'
       ),
       latest_drift AS (
         SELECT status, finished_at
         FROM drift_evaluation_runs
         ORDER BY started_at DESC LIMIT 1
       ),
       incidents AS (
         SELECT count(*) FILTER (WHERE status = 'OPEN') AS open,
                count(*) FILTER (WHERE status = 'ACKNOWLEDGED') AS acknowledged,
                count(*) FILTER (WHERE status = 'RESOLVED') AS resolved
         FROM incidents
       )
       SELECT bounds.window_start,
              bounds.window_end,
              pipeline.runs AS pipeline_runs,
              pipeline.successes AS pipeline_successes,
              pipeline.failures AS pipeline_failures,
              pipeline.latest_run_at AS latest_pipeline_run_at,
              pipeline.latest_successful_ingestion_at,
              quality.runs AS quality_runs,
              quality.successes AS quality_successes,
              quality.failures AS quality_failures,
              latest_quality.status AS latest_quality_status,
              latest_quality.finished_at AS latest_quality_run_at,
              drift.runs AS drift_runs,
              drift.successes AS drift_successes,
              drift.failures AS drift_failures,
              latest_drift.status AS latest_drift_status,
              latest_drift.finished_at AS latest_drift_run_at,
              incidents.open AS open_incidents,
              incidents.acknowledged AS acknowledged_incidents,
              incidents.resolved AS resolved_incidents
       FROM bounds, pipeline, quality, drift, incidents
       LEFT JOIN latest_quality ON true
       LEFT JOIN latest_drift ON true`,
    );
    return rows[0] ? mapReliabilityRow(rows[0]) : reliabilityEmptyState();
  } catch {
    return reliabilityEmptyState();
  }
}
