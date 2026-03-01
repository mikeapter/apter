import "server-only";

const FINNHUB_API_KEY = process.env.FINNHUB_API_KEY;

if (!FINNHUB_API_KEY) {
  console.warn("[Finnhub] Missing FINNHUB_API_KEY");
}

type FinnhubQuoteResponse = {
  c: number; // current
  d: number; // change
  dp: number; // percent change
  h: number; // high
  l: number; // low
  o: number; // open
  pc: number; // prev close
  t: number; // timestamp
};

async function finnhubFetch<T>(path: string): Promise<T> {
  if (!FINNHUB_API_KEY) {
    throw new Error("Missing FINNHUB_API_KEY");
  }

  const url = new URL(`https://finnhub.io/api/v1/${path}`);
  url.searchParams.set("token", FINNHUB_API_KEY);

  const res = await fetch(url.toString(), {
    cache: "no-store",
    headers: { "Cache-Control": "no-store" },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`[Finnhub] ${res.status} ${res.statusText} :: ${text}`);
  }

  return res.json() as Promise<T>;
}

export async function getQuote(symbol: string) {
  const q = await finnhubFetch<FinnhubQuoteResponse>(
    `quote?symbol=${encodeURIComponent(symbol)}`
  );

  return {
    symbol,
    price: Number.isFinite(q.c) ? q.c : null,
    change: Number.isFinite(q.d) ? q.d : null,
    changePct: Number.isFinite(q.dp) ? q.dp : null,
    prevClose: Number.isFinite(q.pc) ? q.pc : null,
    ts: Number.isFinite(q.t) ? q.t : null,
  };
}
