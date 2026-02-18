/**
 * Unified quote consumption layer.
 * All UI components showing prices MUST use this module.
 */

import { authGet } from "./fetchWithAuth";

export type QuoteData = {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  as_of: string;
  session: "REGULAR" | "AFTER_HOURS" | "PRE_MARKET" | "CLOSED";
  delay_seconds: number;
  source: string;
  error?: string;
  message?: string;
};

export type QuotesMeta = {
  serverTime: string;
  maxDelaySeconds: number;
  symbolCount: number;
};

export type QuotesResponse = {
  quotes: Record<string, QuoteData>;
  meta: QuotesMeta;
};

export async function fetchQuotes(symbols: string[]): Promise<QuotesResponse | null> {
  if (!symbols.length) return null;

  const joined = symbols.join(",");
  const result = await authGet<QuotesResponse>(`/api/quotes?symbols=${encodeURIComponent(joined)}`);

  if (result.ok) return result.data;
  return null;
}

export async function fetchSingleQuote(symbol: string): Promise<QuoteData | null> {
  const result = await authGet<QuoteData>(`/api/quotes/${encodeURIComponent(symbol)}`);
  if (result.ok) return result.data;
  return null;
}

export function formatDelayLabel(delaySeconds: number): string {
  if (delaySeconds === 0) return "Real-time";
  if (delaySeconds <= 60) return `Delayed (${delaySeconds}s)`;
  return `Delayed (${Math.round(delaySeconds / 60)}m)`;
}

export function formatSessionLabel(session: string): string {
  switch (session) {
    case "REGULAR": return "Regular Hours";
    case "AFTER_HOURS": return "After Hours";
    case "PRE_MARKET": return "Pre-Market";
    default: return "Market Closed";
  }
}

export function formatAsOf(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "—";
  }
}
