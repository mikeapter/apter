"use client";

import useSWR from "swr";

/** Matches NormalizedQuote from @/lib/market/types */
type Quote = {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  open?: number;
  high?: number;
  low?: number;
  prevClose?: number;
  asOf: string;
  source: string;
  isDelayed: boolean;
};

const fetcher = async (url: string): Promise<Quote> => {
  const res = await fetch(url, {
    cache: "no-store",
    headers: { "Cache-Control": "no-store" },
  });
  if (!res.ok) throw new Error("Quote fetch failed");
  return res.json();
};

export function useLiveQuote(symbol: string, opts?: { refreshMs?: number }) {
  const s = (symbol || "").trim().toUpperCase();
  const refreshMs = opts?.refreshMs ?? 15000;

  const { data, error, isLoading, isValidating } = useSWR(
    s ? `/api/market/quote?symbol=${encodeURIComponent(s)}` : null,
    fetcher,
    {
      refreshInterval: refreshMs,
      revalidateOnFocus: true,
      dedupingInterval: 2000,
      keepPreviousData: true,
    }
  );

  return {
    quote: data,
    isLoading,
    isValidating,
    error,
  };
}

export function formatUsd(v: number | null | undefined) {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  return v.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
  });
}
