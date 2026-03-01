"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { X, Eye, RefreshCw } from "lucide-react";
import { GradeBadge } from "../../components/ui/GradeBadge";
import MarketSearch from "../../components/market/MarketSearch";
import { getMockGrade } from "../../lib/stockData";
import type { NormalizedQuote } from "@/lib/market/types";

const LS_KEY = "apter_watchlist";

type WatchlistItem = {
  ticker: string;
  addedAt: string;
};

type EnrichedItem = WatchlistItem & {
  price: number | null;
  change: number | null;
  changePct: number | null;
  grade: number;
  loading: boolean;
  error: string | null;
};

function loadWatchlist(): WatchlistItem[] {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveWatchlist(items: WatchlistItem[]) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(items));
  } catch {}
}

function formatCurrency(n: number | null): string {
  if (n === null || Number.isNaN(n)) return "\u2014";
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

function formatChange(n: number | null): string {
  if (n === null || Number.isNaN(n)) return "\u2014";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}`;
}

function formatPct(n: number | null): string {
  if (n === null || Number.isNaN(n)) return "\u2014";
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

async function fetchLiveQuote(
  symbol: string
): Promise<NormalizedQuote | null> {
  const res = await fetch(
    `/api/market/quote?symbol=${encodeURIComponent(symbol)}`,
    { cache: "no-store" }
  );
  if (!res.ok) return null;
  const data = await res.json();
  if (data.error) return null;
  return data as NormalizedQuote;
}

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [quotes, setQuotes] = useState<
    Record<
      string,
      {
        price: number | null;
        change: number | null;
        changePct: number | null;
        loading: boolean;
        error: string | null;
      }
    >
  >({});

  useEffect(() => {
    setItems(loadWatchlist());
  }, []);

  const persist = useCallback((next: WatchlistItem[]) => {
    setItems(next);
    saveWatchlist(next);
  }, []);

  const refreshOne = useCallback(async (symbol: string) => {
    setQuotes((prev) => ({
      ...prev,
      [symbol]: { ...(prev[symbol] || {}), loading: true, error: null } as any,
    }));
    try {
      const quote = await fetchLiveQuote(symbol);
      if (!quote) {
        setQuotes((prev) => ({
          ...prev,
          [symbol]: {
            price: null,
            change: null,
            changePct: null,
            loading: false,
            error: "Quote unavailable",
          },
        }));
        return;
      }
      setQuotes((prev) => ({
        ...prev,
        [symbol]: {
          price: quote.price,
          change: quote.change,
          changePct: quote.changePercent,
          loading: false,
          error: null,
        },
      }));
    } catch (e: any) {
      setQuotes((prev) => ({
        ...prev,
        [symbol]: {
          price: null,
          change: null,
          changePct: null,
          loading: false,
          error: e?.message || "Quote fetch failed",
        },
      }));
    }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.allSettled(items.map((i) => refreshOne(i.ticker)));
  }, [items, refreshOne]);

  // Refresh on load + every 30 seconds
  useEffect(() => {
    if (items.length === 0) return;
    refreshAll();
    const t = setInterval(refreshAll, 30_000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items.map((i) => i.ticker).join(",")]);

  function handleAdd(symbol: string) {
    const t = symbol.trim().toUpperCase();
    if (!t) return;
    if (items.some((i) => i.ticker === t)) return;
    persist([...items, { ticker: t, addedAt: new Date().toISOString() }]);
    setTimeout(() => refreshOne(t), 50);
  }

  function handleRemove(t: string) {
    persist(items.filter((i) => i.ticker !== t));
    setQuotes((prev) => {
      const next = { ...prev };
      delete next[t];
      return next;
    });
  }

  const enriched: EnrichedItem[] = items.map((item) => {
    const q = quotes[item.ticker];
    return {
      ...item,
      price: q?.price ?? null,
      change: q?.change ?? null,
      changePct: q?.changePct ?? null,
      grade: getMockGrade(item.ticker),
      loading: q?.loading ?? true,
      error: q?.error ?? null,
    };
  });

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Watchlist</div>
        <div className="text-muted-foreground text-sm">
          Track tickers you are monitoring.
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <MarketSearch onSelect={handleAdd} />
        <button
          onClick={refreshAll}
          className="bt-button h-10 gap-2 shrink-0"
          title="Refresh all quotes"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {enriched.length === 0 ? (
        <div className="bt-panel p-12 flex flex-col items-center justify-center text-muted-foreground">
          <Eye size={40} className="mb-4 opacity-40" />
          <p className="text-sm">
            Your watchlist is empty. Search and add tickers to start monitoring.
          </p>
        </div>
      ) : (
        <div className="bt-panel">
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-panel-2">
                <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  <th className="text-left px-4 py-2.5 font-medium">Ticker</th>
                  <th className="text-right px-4 py-2.5 font-medium">Price</th>
                  <th className="text-right px-4 py-2.5 font-medium">
                    Change
                  </th>
                  <th className="text-right px-4 py-2.5 font-medium">
                    Change %
                  </th>
                  <th className="text-center px-4 py-2.5 font-medium">
                    Grade
                  </th>
                  <th className="text-center px-4 py-2.5 font-medium w-10"></th>
                </tr>
              </thead>
              <tbody>
                {enriched.map((item) => {
                  const color =
                    item.changePct === null
                      ? ""
                      : item.changePct >= 0
                        ? "text-risk-on"
                        : "text-risk-off";
                  return (
                    <tr
                      key={item.ticker}
                      className="border-t border-border hover:bg-muted/30"
                    >
                      <td className="px-4 py-2.5">
                        <Link
                          href={`/stocks/${item.ticker}`}
                          className="font-mono font-semibold hover:underline"
                        >
                          {item.ticker}
                        </Link>
                      </td>
                      <td className="text-right px-4 py-2.5 font-mono">
                        {item.loading ? (
                          <span className="text-muted-foreground animate-pulse">
                            &hellip;
                          </span>
                        ) : (
                          formatCurrency(item.price)
                        )}
                        {item.error && (
                          <div className="mt-1 text-[10px] text-risk-off">
                            {item.error}
                          </div>
                        )}
                      </td>
                      <td
                        className={`text-right px-4 py-2.5 font-mono ${color}`}
                      >
                        {item.loading ? (
                          <span className="text-muted-foreground animate-pulse">
                            &hellip;
                          </span>
                        ) : (
                          formatChange(item.change)
                        )}
                      </td>
                      <td
                        className={`text-right px-4 py-2.5 font-mono ${color}`}
                      >
                        {item.loading ? (
                          <span className="text-muted-foreground animate-pulse">
                            &hellip;
                          </span>
                        ) : (
                          formatPct(item.changePct)
                        )}
                      </td>
                      <td className="text-center px-4 py-2.5">
                        <GradeBadge grade={item.grade} />
                      </td>
                      <td className="text-center px-4 py-2.5">
                        <button
                          type="button"
                          onClick={() => handleRemove(item.ticker)}
                          className="text-muted-foreground hover:text-risk-off"
                          title="Remove from watchlist"
                        >
                          <X size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="text-xs text-muted-foreground">
        Quotes refresh every 30 seconds. Data from Finnhub.
      </div>
    </div>
  );
}
