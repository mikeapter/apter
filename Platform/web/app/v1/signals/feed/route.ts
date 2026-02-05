import { NextResponse } from "next/server";
import { buildSignalsFeed, resolveTierFromRequest } from "../../../api/_shared/devData";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const limitRaw = url.searchParams.get("limit");
  const limit = Math.max(1, Math.min(50, Number(limitRaw || 25) || 25));

  const tier = resolveTierFromRequest(req);
  const data = buildSignalsFeed(tier, limit);

  return NextResponse.json(data);
}
