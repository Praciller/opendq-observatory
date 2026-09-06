import { getDrift } from "../../../../lib/drift";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: Promise<{ dataset: string }> }) {
  const { dataset } = await context.params;
  const response = await getDrift(dataset);
  return Response.json(response, { status: response.message === "Drift data is unavailable." ? 503 : 200 });
}
