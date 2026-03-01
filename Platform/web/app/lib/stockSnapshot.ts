/**
 * Types and fetch helpers for the /api/stocks/{ticker}/snapshot endpoint.
 *
 * This replaces the old local-only stockData for the metrics portion
 * of the stock page, adding TTM/MRQ/Forward labels, data_as_of timestamps,
 * source attribution, and staleness detection.
 */

import { authGet } from "@/lib/fetchWithAuth";

// ─── Metric with metadata ───

export type MetricValue = {
  value: number | null;
  label: string; // "TTM" | "MRQ" | "Forward FY1" | "Forward FY2" | "30-Day"
  data_as_of: string | null;
  source: string;
  null_reason: string | null;
};

// ─── Quote ───

export type QuoteData = {
  symbol: string;
  price: number;
  change: number;
  change_pct: number;
  market_cap: number | null;
  volume: number | null;
  as_of: string;
  session: string;
  delay_seconds: number;
  source: string;
  fetched_at: string;
  provider_latency_ms: number;
};

// ─── Company profile ───

export type CompanyProfile = {
  symbol: string;
  name: string;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  source: string;
  fetched_at: string;
};

// ─── Standardized metrics ───

export type StandardizedMetrics = {
  ticker: string;
  // Valuation
  pe_trailing: MetricValue;
  pe_forward_fy1: MetricValue;
  pe_forward_fy2: MetricValue;
  peg_forward: MetricValue;
  // Growth
  revenue_yoy_ttm: MetricValue;
  eps_yoy_ttm: MetricValue;
  // Profitability
  gross_margin_ttm: MetricValue;
  operating_margin_ttm: MetricValue;
  roe_ttm: MetricValue;
  // Balance Sheet
  debt_to_equity_mrq: MetricValue;
  // Risk
  beta: MetricValue;
  realized_vol_30d: MetricValue;
  // Metadata
  data_as_of: string;
  source: string;
  fetched_at: string;
};

// ─── Forward estimates ───

export type ForwardEstimates = {
  symbol: string;
  fy1_revenue: number | null;
  fy1_eps: number | null;
  fy1_pe: number | null;
  fy1_label: string;
  fy2_revenue: number | null;
  fy2_eps: number | null;
  fy2_pe: number | null;
  fy2_label: string;
  peg_forward: number | null;
  source: string;
  fetched_at: string;
  data_as_of: string | null;
  available: boolean;
  unavailable_reason: string | null;
};

// ─── Data quality ───

export type DataQuality = {
  stale_flags: string[];
  missing_fields: string[];
  provider: string;
  last_updated: string;
};

// ─── Full snapshot ───

export type StockSnapshot = {
  ticker: string;
  quote: QuoteData;
  profile: CompanyProfile;
  fundamentals: StandardizedMetrics;
  forward: ForwardEstimates;
  data_quality: DataQuality;
};

// ─── Fetch helper ───

export async function fetchStockSnapshot(ticker: string, forceRefresh = false) {
  const params = forceRefresh ? "?force_refresh=true" : "";
  return authGet<StockSnapshot>(
    `/api/stocks/${encodeURIComponent(ticker)}/snapshot${params}`
  );
}

// ─── Display helpers ───

export function formatMetricValue(m: MetricValue): string {
  if (m.value === null) return "N/A";
  return m.value.toFixed(1);
}

export function formatMetricWithUnit(
  m: MetricValue,
  unit: "x" | "%" | "" = ""
): string {
  if (m.value === null) return "N/A";
  return `${m.value.toFixed(1)}${unit}`;
}

export function formatDataAsOf(isoDate: string | null): string {
  if (!isoDate) return "N/A";
  try {
    const d = new Date(isoDate);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return isoDate;
  }
}

export function formatFetchedAt(isoDatetime: string): string {
  try {
    const d = new Date(isoDatetime);
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    });
  } catch {
    return isoDatetime;
  }
}

export function hasStaleFlag(
  quality: DataQuality,
  flag: string
): boolean {
  return quality.stale_flags.includes(flag);
}
