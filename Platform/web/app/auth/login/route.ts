import { NextResponse } from "next/server";
import { loginUser } from "../../api/_shared/devData";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  try {
    const data = loginUser(body?.email, body?.password);
    return NextResponse.json(data);
  } catch (e: any) {
    return new Response(e?.message || "Login failed.", { status: 401 });
  }
}
