import { NextResponse } from "next/server";
import { cacheGet, cacheSet } from "@/lib/market/cache";
import { getNormalizedQuoteFinnhub } from "@/lib/market/providers/finnhub";
import type { NormalizedQuote } from "@/lib/market/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NO_CACHE_HEADERS = {
  "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
  Pragma: "no-cache",
  Expires: "0",
  "Surrogate-Control": "no-store",
};

function validateSymbol(raw: string | null): string {
  const s = (raw ?? "").trim().toUpperCase();
  if (!s || s.length > 15) throw new Error("Invalid symbol");
  if (!/^[A-Z0-9.\-]+$/.test(s)) throw new Error("Invalid symbol");
  return s;
}

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const symbol = validateSymbol(searchParams.get("symbol"));

    const cacheKey = `quote:${symbol}`;
    const cached = cacheGet<NormalizedQuote>(cacheKey);
    if (cached) {
      return NextResponse.json(cached, { headers: NO_CACHE_HEADERS });
    }

    const quote = await getNormalizedQuoteFinnhub(symbol);

    // TTL: 10 seconds (adjust up if rate limited)
    cacheSet(cacheKey, quote, 10_000);

    return NextResponse.json(quote, { headers: NO_CACHE_HEADERS });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Quote failed";
    return NextResponse.json(
      { error: message },
      { status: 400, headers: { "Cache-Control": "no-store" } }
    );
  }
}
