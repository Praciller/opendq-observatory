import { getDrift } from "../../../lib/drift";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request) {
  const dataset = new URL(request.url).searchParams.get("dataset") ?? undefined;
  const response = await getDrift(dataset);
  return Response.json(response, { status: response.message === "Drift data is unavailable." ? 503 : 200 });
}
