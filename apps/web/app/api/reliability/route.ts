import { getReliability } from "../../../lib/reliability";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const response = await getReliability();
  return Response.json(response, { status: response.message ? 503 : 200 });
}
