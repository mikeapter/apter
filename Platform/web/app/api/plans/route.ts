import { NextResponse } from "next/server";
import { getPlans, nowIso } from "../_shared/devData";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({ plans: getPlans(), as_of: nowIso() });
}
