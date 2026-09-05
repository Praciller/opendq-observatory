import { buildHealthResponse } from "../../../lib/status";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const health = await buildHealthResponse();
  return Response.json(health, { status: health.status === "healthy" ? 200 : 503 });
}

