import type { SourcesResponse } from "./status";

export const MAX_SOURCE_POLL_AGE_HOURS = 12;

export type SourcePollState = "CURRENT" | "STALE" | "NO_HISTORY" | "DISABLED" | "INVALID_TIME";

export type SourcePollFreshness = {
  slug: string;
  name: string;
  enabled: boolean;
  state: SourcePollState;
  lastSuccessfulPollAt: string | null;
  ageHours: number | null;
};

export type PollReadinessResponse = {
  status: "healthy" | "degraded" | "unavailable";
  checkedAt: string;
  maxPollAgeHours: number;
  sources: SourcePollFreshness[];
  message?: string;
};

/**
 * Measures successful *poll* recency, not source-data event-time freshness.
 * A NO_CHANGE ingestion is a successful poll even when data has not advanced.
 */
export function evaluatePollReadiness(
  response: SourcesResponse,
  databaseHealthy: boolean,
  now: Date = new Date(),
): PollReadinessResponse {
  const checkedAt = now.toISOString();
  const unavailable = !databaseHealthy || response.message === "Source status is unavailable.";
  if (unavailable) {
    return {
      status: "unavailable",
      checkedAt,
      maxPollAgeHours: MAX_SOURCE_POLL_AGE_HOURS,
      sources: [],
      message: "Database or source status is unavailable.",
    };
  }

  const maxAgeMs = MAX_SOURCE_POLL_AGE_HOURS * 60 * 60 * 1000;
  const sources = response.sources.map((source): SourcePollFreshness => {
    const lastSuccessfulPollAt = source.lastSuccessfulIngestion;
    if (!source.enabled) {
      return {
        slug: source.slug,
        name: source.name,
        enabled: false,
        state: "DISABLED",
        lastSuccessfulPollAt,
        ageHours: null,
      };
    }
    if (!lastSuccessfulPollAt) {
      return {
        slug: source.slug,
        name: source.name,
        enabled: true,
        state: "NO_HISTORY",
        lastSuccessfulPollAt: null,
        ageHours: null,
      };
    }

    const timestamp = Date.parse(lastSuccessfulPollAt);
    const ageMs = now.getTime() - timestamp;
    if (!Number.isFinite(timestamp) || ageMs < -5 * 60 * 1000) {
      return {
        slug: source.slug,
        name: source.name,
        enabled: true,
        state: "INVALID_TIME",
        lastSuccessfulPollAt,
        ageHours: null,
      };
    }

    return {
      slug: source.slug,
      name: source.name,
      enabled: true,
      state: ageMs > maxAgeMs ? "STALE" : "CURRENT",
      lastSuccessfulPollAt,
      ageHours: Math.round((Math.max(0, ageMs) / (60 * 60 * 1000)) * 100) / 100,
    };
  });
  const enabled = sources.filter((source) => source.enabled);
  const healthy = enabled.length > 0 && enabled.every((source) => source.state === "CURRENT");

  return {
    status: healthy ? "healthy" : "degraded",
    checkedAt,
    maxPollAgeHours: MAX_SOURCE_POLL_AGE_HOURS,
    sources,
    ...(!healthy && { message: "One or more enabled sources lack a recent successful poll." }),
  };
}
