"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, RefreshCw, Wifi, WifiOff } from "lucide-react";
import { fetchQuote, type FinnhubQuote } from "../../lib/api/market";

const REFRESH_INTERVAL_MS = 15_000; // 15 seconds

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

function formatTime(unix: number): string {
  try {
    const d = new Date(unix * 1000);
    return d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "—";
  }
}

export function QuoteBox({ ticker }: { ticker: string }) {
  const [quote, setQuote] = useState<FinnhubQuote | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = async () => {
    try {
      const data = await fetchQuote(ticker);
      if (data) {
        setQuote(data);
        setError(null);
      } else {
        setError("Unable to load quote");
      }
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    setError(null);
    setQuote(null);

    load();

    // Auto-refresh every 15 seconds
    intervalRef.current = setInterval(load, REFRESH_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  if (loading && !quote) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title flex items-center gap-2">
          LIVE QUOTE
          <Wifi size={12} className="text-muted-foreground" />
        </div>
        <div className="mt-4 flex items-center justify-center gap-2 py-6 text-muted-foreground text-sm">
          <Loader2 size={14} className="animate-spin" />
          Loading quote...
        </div>
      </section>
    );
  }

  if (error && !quote) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title flex items-center gap-2">
          LIVE QUOTE
          <WifiOff size={12} className="text-muted-foreground" />
        </div>
        <div className="mt-4 text-sm text-muted-foreground">{error}</div>
      </section>
    );
  }

  if (!quote) return null;

  const isPositive = quote.change >= 0;
  const changeColor = isPositive ? "text-risk-on" : "text-risk-off";
  const sign = isPositive ? "+" : "";

  return (
    <section className="bt-panel p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="bt-panel-title flex items-center gap-2">
          LIVE QUOTE
          <Wifi size={12} className="text-risk-on" />
        </div>
        <button
          type="button"
          onClick={load}
          className="text-muted-foreground hover:text-foreground transition-colors"
          title="Refresh quote"
        >
          <RefreshCw size={12} />
        </button>
      </div>

      {/* Price */}
      <div className="flex items-baseline gap-2 mb-3">
        <span className="text-2xl font-semibold font-mono">
          {formatCurrency(quote.price)}
        </span>
        <span className={`text-sm font-mono ${changeColor}`}>
          {sign}{formatCurrency(quote.change)} ({sign}{quote.percent_change.toFixed(2)}%)
        </span>
      </div>

      {/* OHLC grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Open</span>
          <span className="font-mono">{formatCurrency(quote.open)}</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Prev Close</span>
          <span className="font-mono">{formatCurrency(quote.prev_close)}</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">High</span>
          <span className="font-mono text-risk-on">{formatCurrency(quote.high)}</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Low</span>
          <span className="font-mono text-risk-off">{formatCurrency(quote.low)}</span>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-3 flex items-center justify-between text-[10px] text-muted-foreground border-t border-border pt-2">
        <span>Source: Finnhub</span>
        <span>As of {formatTime(quote.ts)}</span>
      </div>
    </section>
  );
}
