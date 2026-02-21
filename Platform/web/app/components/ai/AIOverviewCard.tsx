"use client";

import { useState, useEffect } from "react";
import { RefreshCw, AlertTriangle, CheckCircle, Database } from "lucide-react";
import { fetchOverview, type AIResponse } from "../../lib/api/ai";

type Props = {
  tickers?: string[];
  timeframe?: "daily" | "weekly";
};

export function AIOverviewCard({ tickers, timeframe = "daily" }: Props) {
  const [data, setData] = useState<AIResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(force?: boolean) {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchOverview(tickers, timeframe);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load overview");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [tickers?.join(","), timeframe]);

  if (loading && !data) {
    return (
      <div className="rounded-md border border-border bg-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Database size={16} className="text-muted-foreground" />
          <h3 className="text-sm font-semibold">AI Market Overview</h3>
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
          <div className="h-4 bg-muted rounded animate-pulse w-1/2" />
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="rounded-md border border-border bg-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Database size={16} className="text-muted-foreground" />
          <h3 className="text-sm font-semibold">AI Market Overview</h3>
        </div>
        <p className="text-sm text-orange-400">{error}</p>
        <button
          type="button"
          onClick={() => load(true)}
          className="mt-2 text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <RefreshCw size={12} /> Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="rounded-md border border-border bg-card p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database size={16} className="text-muted-foreground" />
          <h3 className="text-sm font-semibold">AI Market Overview</h3>
          {data.cached && (
            <span className="text-[10px] text-muted-foreground bg-panel px-1.5 py-0.5 rounded">cached</span>
          )}
        </div>
        <button
          type="button"
          onClick={() => load(true)}
          disabled={loading}
          className="text-muted-foreground hover:text-foreground transition-colors"
          title="Refresh overview"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Data sources — shown prominently so users see what the AI pulled */}
      {data.data_used?.length > 0 && (
        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground bg-panel rounded px-2 py-1">
          <Database size={10} className="shrink-0" />
          <span>Looking at: {data.data_used.join(", ")}</span>
        </div>
      )}

      {/* Summary */}
      <div>
        <p className="text-sm">{data.summary}</p>
      </div>

      {/* Detail */}
      {data.explanation && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-0.5">Detail</div>
          <p className="text-sm text-muted-foreground">{data.explanation}</p>
        </div>
      )}

      {/* Watchlist items */}
      {data.watchlist_items?.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-0.5">Tickers Mentioned</div>
          <div className="flex flex-wrap gap-1">
            {data.watchlist_items.map((t) => (
              <span key={t} className="text-xs bg-panel border border-border rounded px-1.5 py-0.5 font-mono">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Risk flags */}
      {data.risk_flags?.length > 0 && (
        <div>
          <div className="flex items-center gap-1 mb-0.5">
            <AlertTriangle size={12} className="text-orange-400" />
            <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Risk Observations</span>
          </div>
          <ul className="text-sm space-y-0.5">
            {data.risk_flags.map((flag, i) => (
              <li key={i} className="text-orange-400/80">• {flag}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Checklist */}
      {data.checklist?.length > 0 && (
        <div>
          <div className="flex items-center gap-1 mb-0.5">
            <CheckCircle size={12} className="text-muted-foreground" />
            <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Things to Monitor</span>
          </div>
          <ul className="text-sm space-y-0.5">
            {data.checklist.map((item, i) => (
              <li key={i} className="text-muted-foreground">• {item}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Citations */}
      {data.citations?.length > 0 && (
        <div className="pt-1 border-t border-border/50">
          <span className="text-[10px] text-muted-foreground">
            Sources: {data.citations.join(", ")}
          </span>
        </div>
      )}

      {/* Disclaimer — compact */}
      <div className="pt-1 border-t border-border/50">
        <p className="text-[10px] text-muted-foreground/60">Not investment advice.</p>
      </div>
    </div>
  );
}
