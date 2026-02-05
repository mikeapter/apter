import { NextResponse } from "next/server";
import { getPlan, getSessionFromRequest } from "../../_shared/devData";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const sess = getSessionFromRequest(req);
  if (!sess) return new Response("Unauthorized.", { status: 401 });

  return NextResponse.json({
    tier: sess.tier,
    plan: getPlan(sess.tier),
    status: sess.status,
    updated_at: sess.updated_at,
  });
}
