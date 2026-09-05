import { getQualitySummaries } from "../../../lib/quality";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const response = await getQualitySummaries();
  return Response.json(response, { status: response.message ? 503 : 200 });
}
