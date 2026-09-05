import { getLineage } from "../../../../lib/lineage";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  _request: Request,
  context: { params: Promise<{ dataset: string }> },
) {
  const { dataset } = await context.params;
  const response = await getLineage(dataset);
  return Response.json(response, { status: response.message ? 503 : 200 });
}
