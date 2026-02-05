import { NextResponse } from "next/server";
import { getBearerToken, isPlanTier, setTierForToken } from "../../../_shared/devData";

export const dynamic = "force-dynamic";

const EXPECTED_ADMIN_KEY = (process.env.LOCAL_DEV_API_KEY || "dev").trim();

export async function POST(req: Request) {
  const adminKey = (req.headers.get("x-admin-key") || "").trim();
  if (!adminKey) return new Response("Missing X-Admin-Key.", { status: 401 });

  if (adminKey !== EXPECTED_ADMIN_KEY) {
    return new Response("Invalid admin key.", { status: 403 });
  }

  const token = getBearerToken(req);
  if (!token) return new Response("Missing Bearer token.", { status: 401 });

  const body = await req.json().catch(() => ({}));
  const tier = body?.tier;

  if (!isPlanTier(tier)) return new Response("Invalid tier.", { status: 400 });

  try {
    const sess = setTierForToken(token, tier);
    return NextResponse.json({ ok: true, tier: sess.tier, status: sess.status });
  } catch (e: any) {
    const msg = String(e?.message || e || "");
    if (msg.toLowerCase().includes("invalid session token")) {
      return new Response("Unauthorized.", { status: 401 });
    }
    return new Response("Server error.", { status: 500 });
  }
}
