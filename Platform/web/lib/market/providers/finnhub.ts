import type { NormalizedQuote, SearchResult } from "@/lib/market/types";

const FINNHUB_BASE = "https://finnhub.io/api/v1";

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`Missing env var: ${name}`);
  return v;
}

async function finnhubGet<T>(path: string, params: Record<string, string>): Promise<T> {
  const key = requireEnv("FINNHUB_API_KEY");
  const url = new URL(`${FINNHUB_BASE}${path}`);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  url.searchParams.set("token", key);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Finnhub error ${res.status}: ${text}`);
  }
  return (await res.json()) as T;
}

// Finnhub quote schema: { c, d, dp, h, l, o, pc, t }
type FinnhubQuote = {
  c: number; // current price
  d: number; // change
  dp: number; // percent change
  h: number;
  l: number;
  o: number;
  pc: number; // previous close
  t: number; // unix seconds
};

export async function getNormalizedQuoteFinnhub(
  symbol: string
): Promise<NormalizedQuote> {
  const q = await finnhubGet<FinnhubQuote>("/quote", { symbol });

  // If provider returns zeros on bad symbol or limit, handle it explicitly.
  if (!q || typeof q.c !== "number" || q.c <= 0) {
    throw new Error(`Invalid quote for symbol=${symbol}`);
  }

  return {
    symbol: symbol.toUpperCase(),
    price: q.c,
    change: q.d ?? 0,
    changePercent: q.dp ?? 0,
    open: q.o,
    high: q.h,
    low: q.l,
    prevClose: q.pc,
    asOf: new Date(
      (q.t ?? Math.floor(Date.now() / 1000)) * 1000
    ).toISOString(),
    source: "FINNHUB",
    // Finnhub free tier is typically delayed — keep true unless you know otherwise.
    isDelayed: true,
  };
}

// Finnhub symbol search: /search?q=...
type FinnhubSearchResponse = {
  count: number;
  result: Array<{
    description: string; // company name
    displaySymbol: string;
    symbol: string;
    type: string;
  }>;
};

export async function searchSymbolsFinnhub(
  query: string
): Promise<SearchResult[]> {
  const data = await finnhubGet<FinnhubSearchResponse>("/search", { q: query });

  const results = (data?.result ?? [])
    .filter((r) => r?.symbol && r?.description)
    .slice(0, 10)
    .map((r) => ({
      symbol: r.symbol.toUpperCase(),
      name: r.description,
      type: r.type,
    }));

  return results;
}
