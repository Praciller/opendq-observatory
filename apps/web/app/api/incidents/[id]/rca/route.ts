import { getRca } from "../../../../../lib/rca";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const response = await getRca(id);
  return Response.json(response, { status: response.message === "RCA data is unavailable." ? 503 : 200 });
}
