import { getLineage } from "../../../lib/lineage";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request) {
  const dataset = new URL(request.url).searchParams.get("dataset") ?? "hourly-weather";
  const response = await getLineage(dataset);
  return Response.json(response, { status: response.message ? 503 : 200 });
}
