import { NextResponse } from "next/server";
import { cacheGet, cacheSet } from "@/lib/market/cache";
import { searchSymbolsFinnhub } from "@/lib/market/providers/finnhub";
import { getCompanyLogoUrlFMP } from "@/lib/market/providers/fmp";
import type { SearchResult } from "@/lib/market/types";

function validateQuery(raw: string | null): string {
  const q = (raw ?? "").trim();
  if (!q || q.length < 1) throw new Error("Missing q");
  if (q.length > 40) throw new Error("Query too long");
  return q;
}

export async function GET(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const q = validateQuery(searchParams.get("q"));

    const cacheKey = `search:${q.toLowerCase()}`;
    const cached = cacheGet<SearchResult[]>(cacheKey);
    if (cached) return NextResponse.json(cached);

    const results = await searchSymbolsFinnhub(q);

    // Attach logos (cache-friendly URL)
    const withLogos = results.map((r) => ({
      ...r,
      logoUrl: getCompanyLogoUrlFMP(r.symbol),
    }));

    // TTL: 5 minutes (search results are fine to cache longer)
    cacheSet(cacheKey, withLogos, 5 * 60_000);

    return NextResponse.json(withLogos);
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "Search failed";
    return NextResponse.json({ error: message }, { status: 400 });
  }
}
