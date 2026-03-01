"use client";

import { useState, useEffect } from "react";
import {
  RefreshCw,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Activity,
  Crosshair,
  BarChart3,
  Zap,
  Database,
  CheckCircle,
  Minus,
} from "lucide-react";
import { fetchOverview, type AIResponse } from "../../lib/api/ai";

type Props = {
  tickers?: string[];
  timeframe?: "daily" | "weekly";
};

/* ------------------------------------------------------------------ */
/*  Regime badge                                                       */
/* ------------------------------------------------------------------ */

function RegimeBadge({ label }: { label: string }) {
  const map: Record<string, { cls: string; Icon: typeof TrendingUp }> = {
    "RISK-ON": { cls: "border-risk-on/40 text-risk-on bg-risk-on/5", Icon: TrendingUp },
    "RISK-OFF": { cls: "border-risk-off/40 text-risk-off bg-risk-off/5", Icon: TrendingDown },
    NEUTRAL: { cls: "border-risk-neutral/40 text-risk-neutral bg-risk-neutral/5", Icon: Minus },
  };
  const { cls, Icon } = map[label] ?? map.NEUTRAL;

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-sm border px-2.5 py-1 text-xs font-bold tracking-wide ${cls}`}>
      <Icon size={13} />
      {label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Section header                                                     */
/* ------------------------------------------------------------------ */

function SectionHeader({
  icon: Icon,
  title,
}: {
  icon: typeof Activity;
  title: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-2 pt-3 first:pt-0">
      <Icon size={14} className="text-muted-foreground" />
      <h4 className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground">
        {title}
      </h4>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export function AIOverviewCard({ tickers, timeframe = "daily" }: Props) {
  const [data, setData] = useState<AIResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchOverview(tickers, timeframe);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load briefing");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [tickers?.join(","), timeframe]);

  /* Loading skeleton */
  if (loading && !data) {
    return (
      <div className="rounded-md border border-border bg-card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-muted-foreground" />
          <h3 className="text-sm font-semibold">Daily Brief</h3>
        </div>
        <div className="space-y-2">
          <div className="h-4 bg-muted rounded animate-pulse" />
          <div className="h-4 bg-muted rounded animate-pulse w-5/6" />
          <div className="h-4 bg-muted rounded animate-pulse w-3/4" />
          <div className="h-3 bg-muted rounded animate-pulse w-1/2 mt-4" />
          <div className="h-4 bg-muted rounded animate-pulse w-2/3" />
          <div className="h-4 bg-muted rounded animate-pulse w-4/5" />
        </div>
      </div>
    );
  }

  /* Error state */
  if (error && !data) {
    return (
      <div className="rounded-md border border-border bg-card p-5">
        <div className="flex items-center gap-2 mb-3">
          <Activity size={16} className="text-muted-foreground" />
          <h3 className="text-sm font-semibold">Daily Brief</h3>
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

  if (!data) return null;

  const hasStructuredBrief = !!(
    data.market_regime ||
    data.breadth_internals?.length ||
    data.sector_rotation ||
    data.key_drivers?.length ||
    data.watchlist_focus?.length
  );

  return (
    <div className="rounded-md border border-border bg-card divide-y divide-border">
      {/* ── Header bar ── */}
      <div className="flex items-center justify-between px-5 py-3">
        <div className="flex items-center gap-2.5">
          <Activity size={16} className="text-muted-foreground" />
          <h3 className="text-sm font-semibold">
            {timeframe === "weekly" ? "Weekly Brief" : "Daily Brief"}
          </h3>
          {data.cached && (
            <span className="text-[10px] text-muted-foreground bg-panel px-1.5 py-0.5 rounded border border-border">
              cached
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => load()}
          disabled={loading}
          className="text-muted-foreground hover:text-foreground transition-colors p-1"
          title="Refresh briefing"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* ── Summary headline ── */}
      <div className="px-5 py-4">
        <p className="text-sm leading-relaxed">{data.summary}</p>
      </div>

      {/* ── Data sources ── */}
      {data.data_used?.length > 0 && (
        <div className="px-5 py-2.5 bg-panel/50">
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
            <Database size={10} className="shrink-0" />
            <span>Sources: {data.data_used.join(" · ")}</span>
          </div>
        </div>
      )}

      {/* ── Structured Daily Brief sections ── */}
      {hasStructuredBrief ? (
        <div className="px-5 py-4 space-y-1">
          {/* 1. Market Regime */}
          {data.market_regime && (
            <div>
              <SectionHeader icon={Activity} title="Market Regime" />
              <div className="flex items-start gap-3">
                <RegimeBadge label={data.market_regime.label} />
                {data.market_regime.rationale?.length > 0 && (
                  <ul className="text-sm text-muted-foreground space-y-1 flex-1">
                    {data.market_regime.rationale.map((r, i) => (
                      <li key={i}>
                        <span className="text-foreground/60 mr-1">&mdash;</span>
                        {r}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {/* 2. Breadth & Internals */}
          {data.breadth_internals && data.breadth_internals.length > 0 && (
            <div>
              <SectionHeader icon={BarChart3} title="Breadth & Internals" />
              <ul className="text-sm text-muted-foreground space-y-1">
                {data.breadth_internals.map((item, i) => (
                  <li key={i}>
                    <span className="text-foreground/60 mr-1">&mdash;</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 3. Sector Rotation */}
          {data.sector_rotation && (
            <div>
              <SectionHeader icon={Crosshair} title="Sector Rotation" />
              <div className="grid sm:grid-cols-2 gap-3">
                {/* Strong */}
                {data.sector_rotation.strong?.length > 0 && (
                  <div className="rounded-md border border-risk-on/20 bg-risk-on/5 p-3">
                    <div className="text-[10px] uppercase tracking-[0.14em] text-risk-on font-semibold mb-1.5 flex items-center gap-1">
                      <TrendingUp size={11} />
                      Leading
                    </div>
                    <ul className="text-sm space-y-1">
                      {data.sector_rotation.strong.map((s, i) => (
                        <li key={i}>
                          <span className="text-foreground font-medium">{s.sector}</span>
                          {s.note && (
                            <span className="text-muted-foreground"> &mdash; {s.note}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {/* Weak */}
                {data.sector_rotation.weak?.length > 0 && (
                  <div className="rounded-md border border-risk-off/20 bg-risk-off/5 p-3">
                    <div className="text-[10px] uppercase tracking-[0.14em] text-risk-off font-semibold mb-1.5 flex items-center gap-1">
                      <TrendingDown size={11} />
                      Lagging
                    </div>
                    <ul className="text-sm space-y-1">
                      {data.sector_rotation.weak.map((s, i) => (
                        <li key={i}>
                          <span className="text-foreground font-medium">{s.sector}</span>
                          {s.note && (
                            <span className="text-muted-foreground"> &mdash; {s.note}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 4. Key Drivers */}
          {data.key_drivers && data.key_drivers.length > 0 && (
            <div>
              <SectionHeader icon={Zap} title="Key Drivers" />
              <ul className="text-sm text-muted-foreground space-y-1">
                {data.key_drivers.map((d, i) => (
                  <li key={i}>
                    <span className="text-foreground/60 mr-1">&mdash;</span>
                    {d}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 5. Risk Flags */}
          {data.risk_flags?.length > 0 && (
            <div>
              <SectionHeader icon={AlertTriangle} title="Risk Flags" />
              <ul className="text-sm space-y-1">
                {data.risk_flags.map((flag, i) => (
                  <li key={i} className="text-risk-neutral">
                    <span className="mr-1">&mdash;</span>
                    {flag}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 6. Watchlist Focus */}
          {data.watchlist_focus && data.watchlist_focus.length > 0 && (
            <div>
              <SectionHeader icon={Crosshair} title="Watchlist Focus" />
              <div className="space-y-1.5">
                {data.watchlist_focus.map((item, i) => (
                  <div key={i} className="flex items-baseline gap-2 text-sm">
                    <span className="font-mono font-semibold text-foreground bg-panel border border-border rounded px-1.5 py-0.5 text-xs">
                      {item.ticker}
                    </span>
                    <span className="text-muted-foreground">{item.note}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Fallback for unstructured responses (old format) */
        <div className="px-5 py-4 space-y-3">
          {data.explanation && (
            <div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-0.5">
                Analysis
              </div>
              <p className="text-sm text-muted-foreground">{data.explanation}</p>
            </div>
          )}

          {data.risk_flags?.length > 0 && (
            <div>
              <div className="flex items-center gap-1 mb-0.5">
                <AlertTriangle size={12} className="text-risk-neutral" />
                <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">
                  Risk Observations
                </span>
              </div>
              <ul className="text-sm space-y-0.5">
                {data.risk_flags.map((flag, i) => (
                  <li key={i} className="text-risk-neutral">&mdash; {flag}</li>
                ))}
              </ul>
            </div>
          )}

          {data.watchlist_items?.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-0.5">
                Tickers Mentioned
              </div>
              <div className="flex flex-wrap gap-1">
                {data.watchlist_items.map((t) => (
                  <span
                    key={t}
                    className="text-xs bg-panel border border-border rounded px-1.5 py-0.5 font-mono"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Context / explanation ── */}
      {hasStructuredBrief && data.explanation && (
        <div className="px-5 py-3">
          <p className="text-sm text-muted-foreground leading-relaxed">
            {data.explanation}
          </p>
        </div>
      )}

      {/* ── Things to monitor ── */}
      {data.checklist?.length > 0 && (
        <div className="px-5 py-3">
          <div className="flex items-center gap-1 mb-1.5">
            <CheckCircle size={12} className="text-muted-foreground" />
            <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">
              Monitor This Period
            </span>
          </div>
          <ul className="text-sm space-y-0.5">
            {data.checklist.map((item, i) => (
              <li key={i} className="text-muted-foreground">&mdash; {item}</li>
            ))}
          </ul>
        </div>
      )}

      {/* ── Citations ── */}
      {data.citations?.length > 0 && (
        <div className="px-5 py-2.5">
          <span className="text-[10px] text-muted-foreground">
            Sources: {data.citations.join(" · ")}
          </span>
        </div>
      )}

      {/* ── Disclaimer ── */}
      <div className="px-5 py-2.5 bg-panel/30">
        <p className="text-[10px] text-muted-foreground/60">
          Not investment advice. Data is informational only and may be delayed or incomplete.
        </p>
      </div>
    </div>
  );
}
