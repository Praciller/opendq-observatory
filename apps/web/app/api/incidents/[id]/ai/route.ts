import { getAiAnalysis } from "../../../../../lib/ai";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const response = await getAiAnalysis(id);
  return Response.json(response, { status: response.message === "AI analysis data is unavailable." ? 503 : 200 });
}
