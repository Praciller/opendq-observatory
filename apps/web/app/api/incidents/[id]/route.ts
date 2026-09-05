import { getIncident } from "../../../../lib/incidents";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const response = await getIncident(id);
  return Response.json(response, { status: response.message && !response.incident ? 404 : 200 });
}
