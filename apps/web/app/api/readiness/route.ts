import { evaluatePollReadiness } from "../../../lib/source-freshness";
import { buildHealthResponse, getSourceStatuses } from "../../../lib/status";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const health = await buildHealthResponse();
  const sources =
    health.status === "healthy"
      ? await getSourceStatuses()
      : { sources: [], message: "Source status is unavailable." };
  const result = evaluatePollReadiness(sources, health.status === "healthy");
  return Response.json(result, {
    status: result.status === "healthy" ? 200 : 503,
    headers: { "Cache-Control": "no-store" },
  });
}
