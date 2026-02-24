/**
 * Typed API client for Finnhub-backed market data endpoints.
 *
 * All calls go through the FastAPI backend — Finnhub key stays server-side.
 */

import { authGet } from "@/lib/fetchWithAuth";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type FinnhubQuote = {
  ticker: string;
  price: number;
  change: number;
  percent_change: number;
  high: number;
  low: number;
  open: number;
  prev_close: number;
  ts: number;
  source: string;
};

export type FinnhubCandles = {
  ticker: string;
  resolution: string;
  from: number;
  to: number;
  t: number[];
  o: number[];
  h: number[];
  l: number[];
  c: number[];
  v: number[];
  source: string;
};

export type FinnhubProfile = {
  ticker: string;
  name: string;
  country: string;
  currency: string;
  exchange: string;
  ipo: string;
  market_cap: number;
  industry: string;
  logo: string;
  weburl: string;
  source: string;
};

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------

/**
 * Fetch a real-time-ish quote for a single ticker.
 * Backend caches for ~20s.
 */
export async function fetchQuote(ticker: string): Promise<FinnhubQuote | null> {
  const result = await authGet<FinnhubQuote>(
    `/api/market/quote?ticker=${encodeURIComponent(ticker)}`,
  );
  if (result.ok) return result.data;
  return null;
}

/**
 * Fetch OHLCV candle data for a ticker.
 *
 * @param ticker     Stock symbol
 * @param resolution Candle resolution: "1" | "5" | "15" | "30" | "60" | "D" | "W" | "M"
 * @param from       Start UNIX timestamp
 * @param to         End UNIX timestamp
 */
export async function fetchCandles(
  ticker: string,
  resolution: string,
  from: number,
  to: number,
): Promise<FinnhubCandles | null> {
  const params = new URLSearchParams({
    ticker,
    resolution,
    from: String(from),
    to: String(to),
  });

  const result = await authGet<FinnhubCandles>(
    `/api/market/candles?${params.toString()}`,
  );
  if (result.ok) return result.data;
  return null;
}

/**
 * Fetch company profile for a ticker.
 * Backend caches for ~10 minutes.
 */
export async function fetchProfile(
  ticker: string,
): Promise<FinnhubProfile | null> {
  const result = await authGet<FinnhubProfile>(
    `/api/market/profile?ticker=${encodeURIComponent(ticker)}`,
  );
  if (result.ok) return result.data;
  return null;
}
