"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Activity,
  BarChart3,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  RefreshCw,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

// ─── Types ─────────────────────────────────────────────────────────────────

interface MarketBriefQuote {
  symbol: string;
  price: number;
  previousClose: number;
  change: number;
  changePercent: number;
  dayHigh: number | null;
  dayLow: number | null;
  timestampUtc: string;
}

interface MarketBriefData {
  asOfUtc: string;
  narrative: string;
  regime: string;
  volatility: {
    label: string;
    value: number | null;
    method: string;
  };
  breadth: {
    label: string;
    green: number;
    red: number;
    total: number;
    explanation: string;
  };
  whatChanged: string[];
  catalysts: string[];
  quotes: Record<string, MarketBriefQuote>;
  symbols: string[];
  cacheAgeSeconds: number;
  stale?: boolean;
  error?: string;
}

// ─── Helpers ───────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

function volatilityColor(label: string): string {
  switch (label) {
    case "Low":
      return "bt-chip bt-chip-on";
    case "Moderate":
      return "bt-chip bt-chip-neutral";
    case "Elevated":
      return "bt-chip bt-chip-off";
    case "High":
      return "bg-red-600/20 text-red-400 border border-red-500/30 text-[10px] font-semibold px-2 py-0.5 rounded";
    default:
      return "bt-chip bt-chip-neutral";
  }
}

function regimeColor(regime: string): string {
  switch (regime) {
    case "Risk-On":
      return "bt-chip bt-chip-on";
    case "Risk-Off":
      return "bt-chip bt-chip-off";
    default:
      return "bt-chip bt-chip-neutral";
  }
}

function regimeIcon(regime: string) {
  switch (regime) {
    case "Risk-On":
      return <TrendingUp size={12} className="text-risk-on" />;
    case "Risk-Off":
      return <TrendingDown size={12} className="text-risk-off" />;
    default:
      return <Minus size={12} className="text-muted-foreground" />;
  }
}

function breadthColor(label: string): string {
  switch (label) {
    case "Broad":
      return "bt-chip bt-chip-on";
    case "Narrow":
      return "bt-chip bt-chip-off";
    default:
      return "bt-chip bt-chip-neutral";
  }
}

function formatTime(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    });
  } catch {
    return isoStr;
  }
}

// ─── Component ─────────────────────────────────────────────────────────────

export function MarketBriefPanel() {
  const [brief, setBrief] = useState<MarketBriefData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const fetchBrief = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/api/market-brief`, {
        cache: "no-store",
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: MarketBriefData = await res.json();
      if (data.error && !data.narrative) {
        throw new Error(data.error);
      }
      setBrief(data);
    } catch (e: any) {
      setError(e?.message || "Failed to load market brief");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBrief();
    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchBrief, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchBrief]);

  // ── Loading state ────────────────────────────────────────────────────

  if (loading && !brief) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">MARKET INTELLIGENCE BRIEF</div>
        <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
          <RefreshCw size={14} className="animate-spin" />
          Loading market data...
        </div>
      </section>
    );
  }

  // ── Error state (no data at all) ─────────────────────────────────────

  if (error && !brief) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">MARKET INTELLIGENCE BRIEF</div>
        <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
          <AlertTriangle size={14} className="text-yellow-500" />
          {error}
        </div>
        <button
          onClick={fetchBrief}
          className="mt-2 text-xs text-primary hover:underline"
        >
          Retry
        </button>
      </section>
    );
  }

  if (!brief) return null;

  const isCached = brief.cacheAgeSeconds > 0;
  const isStale = brief.stale === true;

  return (
    <section className="bt-panel p-4">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="bt-panel-title flex items-center gap-2">
          <Activity size={14} />
          MARKET INTELLIGENCE BRIEF
        </div>
        <div className="flex items-center gap-2">
          {isCached && (
            <span className="text-[10px] text-muted-foreground flex items-center gap-1">
              <Clock size={10} />
              cached {Math.round(brief.cacheAgeSeconds / 60)}m ago
            </span>
          )}
          {isStale && (
            <span className="text-[10px] text-yellow-500 flex items-center gap-1">
              <AlertTriangle size={10} />
              stale
            </span>
          )}
          <button
            onClick={fetchBrief}
            disabled={loading}
            className="text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* ── Label chips row ────────────────────────────────────────── */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {/* Regime */}
        <div className="flex items-center gap-1.5">
          {regimeIcon(brief.regime)}
          <span className={regimeColor(brief.regime)}>
            {brief.regime}
          </span>
        </div>

        {/* Volatility */}
        <div className="flex items-center gap-1.5">
          <BarChart3 size={12} className="text-muted-foreground" />
          <span className={volatilityColor(brief.volatility.label)}>
            Vol: {brief.volatility.label}
            {brief.volatility.value != null && (
              <> ({brief.volatility.value})</>
            )}
          </span>
        </div>

        {/* Breadth */}
        <div className="flex items-center gap-1.5">
          <span className={breadthColor(brief.breadth.label)}>
            Breadth: {brief.breadth.label}
          </span>
          <span className="text-[10px] text-muted-foreground">
            ({brief.breadth.green}G / {brief.breadth.red}R)
          </span>
        </div>
      </div>

      {/* ── Narrative ──────────────────────────────────────────────── */}
      <div className="mt-3 text-sm text-muted-foreground leading-relaxed">
        {brief.narrative}
      </div>

      {/* ── Expand/collapse for details ────────────────────────────── */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-3 flex items-center gap-1 text-xs text-primary hover:underline"
      >
        {expanded ? (
          <>
            <ChevronUp size={12} /> Less detail
          </>
        ) : (
          <>
            <ChevronDown size={12} /> More detail
          </>
        )}
      </button>

      {expanded && (
        <div className="mt-3 space-y-4">
          {/* ── What Changed ─────────────────────────────────────── */}
          {brief.whatChanged.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-medium mb-1.5">
                What Changed
              </div>
              <ul className="space-y-1">
                {brief.whatChanged.map((item, i) => (
                  <li
                    key={i}
                    className="text-sm text-muted-foreground leading-relaxed flex items-start gap-2"
                  >
                    <span className="mt-1.5 h-1 w-1 rounded-full bg-muted-foreground/50 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* ── Catalysts ────────────────────────────────────────── */}
          {brief.catalysts.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-medium mb-1.5">
                Catalysts & Observations
              </div>
              <ul className="space-y-1">
                {brief.catalysts.map((item, i) => (
                  <li
                    key={i}
                    className="text-sm text-muted-foreground leading-relaxed flex items-start gap-2"
                  >
                    <span className="mt-1.5 h-1 w-1 rounded-full bg-muted-foreground/50 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* ── Quote chips ──────────────────────────────────────── */}
          <div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-medium mb-1.5">
              Quotes
            </div>
            <div className="flex flex-wrap gap-2">
              {brief.symbols
                .filter((s) => s !== "^VIX")
                .map((sym) => {
                  const q = brief.quotes[sym];
                  if (!q) return null;
                  const isUp = q.changePercent > 0;
                  const color = isUp ? "text-risk-on" : q.changePercent < 0 ? "text-risk-off" : "text-muted-foreground";
                  return (
                    <div
                      key={sym}
                      className="rounded border border-border bg-panel-2 px-2 py-1 text-xs font-mono"
                    >
                      <span className="font-semibold">{sym}</span>{" "}
                      <span>${q.price.toFixed(2)}</span>{" "}
                      <span className={color}>
                        {isUp ? "+" : ""}
                        {q.changePercent.toFixed(2)}%
                      </span>
                    </div>
                  );
                })}
            </div>
          </div>

          {/* ── Data source + timestamp ──────────────────────────── */}
          <div className="text-[10px] text-muted-foreground border-t border-border pt-2">
            Data: Yahoo Finance {brief.volatility.method === "VIX" ? "/ VIX" : "/ SPY range proxy"}.
            As of {formatTime(brief.asOfUtc)}.
            {isCached && <> Cached {Math.round(brief.cacheAgeSeconds / 60)}m ago.</>}
          </div>
        </div>
      )}
    </section>
  );
}
