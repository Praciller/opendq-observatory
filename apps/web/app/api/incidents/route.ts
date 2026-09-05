import { getIncidents } from "../../../lib/incidents";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const response = await getIncidents({
    status: url.searchParams.get("status") ?? undefined,
    dataset: url.searchParams.get("dataset") ?? undefined,
    severity: url.searchParams.get("severity") ?? undefined,
  });
  return Response.json(response, { status: response.message ? 503 : 200 });
}
