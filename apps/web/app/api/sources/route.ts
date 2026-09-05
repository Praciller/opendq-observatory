import { getSourceStatuses } from "../../../lib/status";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const response = await getSourceStatuses();
  return Response.json(response, { status: response.message === "Source status is unavailable." ? 503 : 200 });
}

