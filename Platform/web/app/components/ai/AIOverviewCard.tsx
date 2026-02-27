"use client";

import { useState, useEffect } from "react";
import {
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Database,
  Activity,
  BarChart3,
} from "lucide-react";
import {
  fetchMarketIntelligence,
  fetchOverview,
  type MarketIntelligenceBrief,
  type AIResponse,
} from "../../lib/api/ai";
import { COMPLIANCE } from "../../lib/compliance";

type Props = {
  tickers?: string[];
  timeframe?: "daily" | "weekly";
};

export function AIOverviewCard({ tickers, timeframe = "daily" }: Props) {
  const [brief, setBrief] = useState<MarketIntelligenceBrief | null>(null);
  const [legacy, setLegacy] = useState<AIResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      // Use new market intelligence endpoint when no ticker filter is applied
      if (!tickers?.length) {
        const result = await fetchMarketIntelligence(timeframe);
        setBrief(result);
        setLegacy(null);
      } else {
        // Filtered by tickers — fall back to legacy overview
        const result = await fetchOverview(tickers, timeframe);
        setLegacy(result);
        setBrief(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load market brief");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [tickers?.join(","), timeframe]);

  // ── Loading skeleton ──
  if (loading && !brief && !legacy) {
    return (
      <div className="rounded-md border border-border bg-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Activity size={16} className="text-muted-foreground" />
          <h3 className="text-sm font-semibold">Market Intelligence Brief</h3>
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
          <div className="h-4 bg-muted rounded animate-pulse w-1/2" />
        </div>
      </div>
    );
  }

  // ── Error state ──
  if (error && !brief && !legacy) {
    return (
      <div className="rounded-md border border-border bg-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Activity size={16} className="text-muted-foreground" />
          <h3 className="text-sm font-semibold">Market Intelligence Brief</h3>
        </div>
        <p className="text-sm text-orange-400">{error}</p>
        <button
          type="button"
          onClick={() => load()}
          className="mt-2 text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <RefreshCw size={12} /> Retry
        </button>
      </div>
    );
  }

  // ── New Market Intelligence Brief ──
  if (brief) {
    return (
      <div className="rounded-md border border-border bg-card p-4 space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-muted-foreground" />
            <h3 className="text-sm font-semibold">Market Intelligence Brief</h3>
            {brief.cached && (
              <span className="text-[10px] text-muted-foreground bg-panel px-1.5 py-0.5 rounded">cached</span>
            )}
          </div>
          <button
            type="button"
            onClick={() => load()}
            disabled={loading}
            className="text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh brief"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>

        {/* Data sources */}
        {brief.data_sources?.length > 0 && (
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground bg-panel rounded px-2 py-1">
            <Database size={10} className="shrink-0" />
            <span>Data sources: {brief.data_sources.join(", ")}</span>
          </div>
        )}

        {/* Executive summary */}
        <div>
          <p className="text-sm">{brief.executive_summary}</p>
        </div>

        {/* Risk Dashboard */}
        {brief.risk_dashboard && (
          <div>
            <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-1.5">
              Risk Dashboard
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="rounded-md border border-border bg-panel-2 px-2.5 py-1.5">
                <div className="text-[9px] uppercase tracking-[0.14em] text-muted-foreground">Regime</div>
                <div className="text-xs font-medium mt-0.5">{brief.risk_dashboard.regime}</div>
              </div>
              <div className="rounded-md border border-border bg-panel-2 px-2.5 py-1.5">
                <div className="text-[9px] uppercase tracking-[0.14em] text-muted-foreground">Volatility</div>
                <div className="text-xs font-medium mt-0.5">{brief.risk_dashboard.volatility_context}</div>
              </div>
              <div className="rounded-md border border-border bg-panel-2 px-2.5 py-1.5">
                <div className="text-[9px] uppercase tracking-[0.14em] text-muted-foreground">Breadth</div>
                <div className="text-xs font-medium mt-0.5">{brief.risk_dashboard.breadth_context}</div>
              </div>
            </div>
          </div>
        )}

        {/* What Changed */}
        {brief.what_changed?.length > 0 && (
          <div>
            <div className="flex items-center gap-1 mb-0.5">
              <BarChart3 size={12} className="text-muted-foreground" />
              <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">
                What Changed
              </span>
            </div>
            <ul className="text-sm space-y-0.5">
              {brief.what_changed.map((item, i) => (
                <li key={i} className="text-muted-foreground">&bull; {item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Catalysts */}
        {brief.catalysts?.length > 0 && (
          <div>
            <div className="flex items-center gap-1 mb-0.5">
              <AlertTriangle size={12} className="text-orange-400" />
              <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">
                Catalysts to Monitor
              </span>
            </div>
            <ul className="text-sm space-y-0.5">
              {brief.catalysts.map((item, i) => (
                <li key={i} className="text-orange-400/80">&bull; {item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Timestamp */}
        {brief.as_of && (
          <div className="text-[10px] text-muted-foreground/60">
            As of {brief.as_of}
          </div>
        )}

        {/* Disclaimer */}
        <div className="pt-1 border-t border-border/50">
          <p className="text-[10px] text-muted-foreground/60">{COMPLIANCE.NOT_INVESTMENT_ADVICE}</p>
        </div>
      </div>
    );
  }

  // ── Legacy AIResponse (when tickers are selected) ──
  if (legacy) {
    return (
      <div className="rounded-md border border-border bg-card p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity size={16} className="text-muted-foreground" />
            <h3 className="text-sm font-semibold">Market Intelligence Brief</h3>
            {legacy.cached && (
              <span className="text-[10px] text-muted-foreground bg-panel px-1.5 py-0.5 rounded">cached</span>
            )}
          </div>
          <button
            type="button"
            onClick={() => load()}
            disabled={loading}
            className="text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh brief"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>

        {legacy.data_used?.length > 0 && (
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground bg-panel rounded px-2 py-1">
            <Database size={10} className="shrink-0" />
            <span>Data sources: {legacy.data_used.join(", ")}</span>
          </div>
        )}

        <div>
          <p className="text-sm">{legacy.summary}</p>
        </div>

        {legacy.explanation && (
          <div>
            <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-0.5">Detail</div>
            <p className="text-sm text-muted-foreground">{legacy.explanation}</p>
          </div>
        )}

        {legacy.watchlist_items?.length > 0 && (
          <div>
            <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-0.5">Tickers Mentioned</div>
            <div className="flex flex-wrap gap-1">
              {legacy.watchlist_items.map((t) => (
                <span key={t} className="text-xs bg-panel border border-border rounded px-1.5 py-0.5 font-mono">
                  {t}
                </span>
              ))}
            </div>
          </div>
        )}

        {legacy.risk_flags?.length > 0 && (
          <div>
            <div className="flex items-center gap-1 mb-0.5">
              <AlertTriangle size={12} className="text-orange-400" />
              <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Risk Observations</span>
            </div>
            <ul className="text-sm space-y-0.5">
              {legacy.risk_flags.map((flag, i) => (
                <li key={i} className="text-orange-400/80">&bull; {flag}</li>
              ))}
            </ul>
          </div>
        )}

        {legacy.checklist?.length > 0 && (
          <div>
            <div className="flex items-center gap-1 mb-0.5">
              <CheckCircle size={12} className="text-muted-foreground" />
              <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Things to Monitor</span>
            </div>
            <ul className="text-sm space-y-0.5">
              {legacy.checklist.map((item, i) => (
                <li key={i} className="text-muted-foreground">&bull; {item}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="pt-1 border-t border-border/50">
          <p className="text-[10px] text-muted-foreground/60">{COMPLIANCE.NOT_INVESTMENT_ADVICE}</p>
        </div>
      </div>
    );
  }

  return null;
}
