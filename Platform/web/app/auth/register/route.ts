import { NextResponse } from "next/server";
import { registerUser } from "../../api/_shared/devData";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  try {
    const data = registerUser(body?.email, body?.password);
    return NextResponse.json(data);
  } catch (e: any) {
    return new Response(e?.message || "Register failed.", { status: 400 });
  }
}
