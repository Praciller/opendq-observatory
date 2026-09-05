import { query } from "./db";

export type HealthResponse = {
  status: "healthy" | "degraded";
  database: "healthy" | "unavailable";
};

export type SourceStatus = {
  slug: string;
  name: string;
  enabled: boolean;
  lastSuccessfulIngestion: string | null;
  hasIngestion: boolean;
};

export type SourcesResponse = {
  sources: SourceStatus[];
  message?: string;
};

export async function checkDatabase(): Promise<boolean> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    await Promise.race([
      query("SELECT 1"),
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new Error("database health check timed out")), 1000);
      }),
    ]);
    return true;
  } catch {
    return false;
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export async function buildHealthResponse(
  check: () => Promise<boolean> = checkDatabase,
): Promise<HealthResponse> {
  const databaseHealthy = await check();
  return databaseHealthy
    ? { status: "healthy", database: "healthy" }
    : { status: "degraded", database: "unavailable" };
}

export function sourceEmptyState(): SourcesResponse {
  return { sources: [], message: "No source ingestion has been recorded yet." };
}

export async function getSourceStatuses(): Promise<SourcesResponse> {
  try {
    const rows = await query<{
      slug: string;
      name: string;
      enabled: boolean;
      last_successful_ingestion: Date | null;
      has_ingestion: boolean;
    }>(
      `SELECT s.slug, s.name, s.enabled,
              max(ir.finished_at) FILTER (WHERE ir.status IN ('SUCCESS', 'NO_CHANGE')) AS last_successful_ingestion,
              max(ir.finished_at) FILTER (WHERE ir.status IN ('SUCCESS', 'NO_CHANGE')) IS NOT NULL AS has_ingestion
       FROM sources s
       LEFT JOIN ingestion_runs ir ON ir.source_id = s.id
       GROUP BY s.id, s.slug, s.name, s.enabled
       ORDER BY s.id`,
    );
    if (rows.length === 0) return sourceEmptyState();
    return {
      sources: rows.map((row) => ({
        slug: row.slug,
        name: row.name,
        enabled: row.enabled,
        lastSuccessfulIngestion: row.last_successful_ingestion?.toISOString() ?? null,
        hasIngestion: row.has_ingestion,
      })),
    };
  } catch {
    return { sources: [], message: "Source status is unavailable." };
  }
}
