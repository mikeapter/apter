"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Loader2,
  AlertCircle,
  AlertTriangle,
  Info,
  Clock,
  Database,
  ShieldAlert,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { getStockDetail, generateStockChartData } from "../../lib/stockData";
import { GradeBadge } from "../ui/GradeBadge";
import { ClientOnly } from "../ClientOnly";
import { ConvictionScoreCard } from "../dashboard/ConvictionScoreCard";
import { CandlestickChart } from "./CandlestickChart";
import {
  fetchStockIntelligence,
  fetchAptRating,
  type StockIntelligenceBrief,
  type AptRatingResponse,
} from "../../lib/api/ai";
import { COMPLIANCE } from "../../lib/compliance";
import {
  fetchStockSnapshot,
  formatDataAsOf,
  formatFetchedAt,
  formatMetricWithUnit,
  hasStaleFlag,
  type StockSnapshot,
  type MetricValue,
  type DataQuality,
} from "../../lib/stockSnapshot";
import type { NormalizedQuote } from "@/lib/market/types";
import { FeatureGate } from "../billing/FeatureGate";
import { TierBadge } from "../billing/TierBadge";
import { GroundedBriefPanel } from "./GroundedBriefPanel";

type TimeRange = "1D" | "1W" | "1M" | "3M" | "1Y" | "ALL";
const TIME_RANGES: TimeRange[] = ["1D", "1W", "1M", "3M", "1Y", "ALL"];

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

function formatMarketCap(n: number | null): string {
  if (n === null || n === undefined) return "N/A";
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`;
  return `$${n.toLocaleString()}`;
}

/* ─── Price Chart ─── */

function PriceChart({ ticker, range }: { ticker: string; range: TimeRange }) {
  const data = useMemo(() => generateStockChartData(ticker, range), [ticker, range]);

  return (
    <ClientOnly fallback={<div className="h-[250px] flex items-center justify-center text-muted-foreground text-sm">Loading chart...</div>}>
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--risk-on))" stopOpacity={0.3} />
              <stop offset="100%" stopColor="hsl(var(--risk-on))" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `$${v.toFixed(0)}`}
            width={60}
          />
          <Tooltip
            contentStyle={{
              background: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 4,
              fontSize: 12,
            }}
          />
          <Area
            type="monotone"
            dataKey="price"
            stroke="hsl(var(--risk-on))"
            fill="url(#priceGrad)"
            strokeWidth={1.5}
            name="Price"
          />
        </AreaChart>
      </ResponsiveContainer>
    </ClientOnly>
  );
}

/* ─── Label badge component ─── */

function LabelBadge({ label }: { label: string }) {
  const colorMap: Record<string, string> = {
    TTM: "bg-blue-500/10 text-blue-400 border-blue-500/30",
    MRQ: "bg-purple-500/10 text-purple-400 border-purple-500/30",
    "Forward FY1": "bg-amber-500/10 text-amber-400 border-amber-500/30",
    "Forward FY2": "bg-amber-500/10 text-amber-400 border-amber-500/30",
    Forward: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    "30-Day": "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
  };
  const cls = colorMap[label] || "bg-muted/50 text-muted-foreground border-border";
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider border ${cls}`}>
      {label}
    </span>
  );
}

/* ─── Metric row component ─── */

function MetricRow({ name, metric, unit = "" }: { name: string; metric: MetricValue; unit?: "x" | "%" | "" }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">{name}</span>
        <LabelBadge label={metric.label} />
      </div>
      <div className="text-right">
        {metric.value !== null ? (
          <span className="text-sm font-mono font-medium">
            {formatMetricWithUnit(metric, unit)}
            {unit}
          </span>
        ) : (
          <span
            className="text-xs text-muted-foreground italic cursor-help"
            title={metric.null_reason || "Data unavailable"}
          >
            N/A
          </span>
        )}
      </div>
    </div>
  );
}

/* ─── Data source footer ─── */

function DataSourceFooter({
  dataAsOf,
  fetchedAt,
  source,
  quality,
}: {
  dataAsOf: string;
  fetchedAt: string;
  source: string;
  quality: DataQuality;
}) {
  const isStale =
    hasStaleFlag(quality, "fundamentals_old") ||
    hasStaleFlag(quality, "no_fundamentals");

  return (
    <div className="mt-3 pt-2 border-t border-border space-y-1">
      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
        {isStale && (
          <span className="flex items-center gap-1 text-amber-400" title="Fundamentals may be delayed.">
            <AlertTriangle size={10} />
          </span>
        )}
        <span>Data as of: {formatDataAsOf(dataAsOf)}</span>
        <span>&middot;</span>
        <span>Fetched: {formatFetchedAt(fetchedAt)}</span>
        <span>&middot;</span>
        <span>Source: {source}</span>
      </div>
      {isStale && (
        <div className="flex items-center gap-1 text-[10px] text-amber-400">
          <AlertTriangle size={10} />
          Fundamentals may be delayed. Data is based on the last reported period.
        </div>
      )}
      {hasStaleFlag(quality, "no_forward_estimates") && (
        <div className="text-[10px] text-muted-foreground italic">
          Forward estimates unavailable with current data source.
        </div>
      )}
    </div>
  );
}

/* ─── Fundamentals panel (from snapshot) ─── */

function FundamentalsPanel({ snapshot }: { snapshot: StockSnapshot }) {
  const f = snapshot.fundamentals;
  const fwd = snapshot.forward;

  return (
    <section className="bt-panel p-4">
      <div className="bt-panel-title">FUNDAMENTALS &amp; METRICS</div>

      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        {/* Valuation */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
            Valuation
          </div>
          <MetricRow name="P/E Ratio" metric={f.pe_trailing} unit="x" />
          <MetricRow name="P/E Forward" metric={f.pe_forward_fy1} unit="x" />
          <MetricRow name="P/E Forward" metric={f.pe_forward_fy2} unit="x" />
          <MetricRow name="PEG" metric={f.peg_forward} unit="x" />
        </div>

        {/* Growth */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
            Growth
          </div>
          <MetricRow name="Revenue YoY" metric={f.revenue_yoy_ttm} unit="%" />
          <MetricRow name="EPS YoY" metric={f.eps_yoy_ttm} unit="%" />
        </div>

        {/* Profitability */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
            Profitability
          </div>
          <MetricRow name="Gross Margin" metric={f.gross_margin_ttm} unit="%" />
          <MetricRow name="Operating Margin" metric={f.operating_margin_ttm} unit="%" />
          <MetricRow name="ROE" metric={f.roe_ttm} unit="%" />
        </div>

        {/* Risk & Balance Sheet */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
            Risk &amp; Balance Sheet
          </div>
          <MetricRow name="Debt/Equity" metric={f.debt_to_equity_mrq} unit="x" />
          <MetricRow name="Beta" metric={f.beta} unit="" />
          <MetricRow name="30d Volatility" metric={f.realized_vol_30d} unit="%" />
        </div>
      </div>

      {/* Forward estimates notice */}
      {!fwd.available && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-border bg-panel-2 px-3 py-2">
          <Info size={12} className="text-muted-foreground mt-0.5 shrink-0" />
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            Forward estimates unavailable with current data source. Integrate a
            provider like FMP, Polygon, or Finnhub for FY1/FY2 consensus
            estimates and forward P/E.
          </p>
        </div>
      )}

      <DataSourceFooter
        dataAsOf={f.data_as_of}
        fetchedAt={f.fetched_at}
        source={f.source}
        quality={snapshot.data_quality}
      />
    </section>
  );
}

/* ─── Apter Rating Card ─── */

function ratingColor(rating: number): string {
  if (rating >= 8) return "text-risk-on";
  if (rating >= 6) return "text-risk-on/80";
  if (rating >= 4) return "text-yellow-400";
  return "text-risk-off";
}

function AptRatingCard({ ticker }: { ticker: string }) {
  const [data, setData] = useState<AptRatingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);

    fetchAptRating(ticker)
      .then((res) => setData(res))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load rating"))
      .finally(() => setLoading(false));
  }, [ticker]);

  if (loading) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">APTER RATING</div>
        <div className="mt-4 flex items-center justify-center gap-2 py-6 text-muted-foreground text-sm">
          <Loader2 size={14} className="animate-spin" />
          Computing...
        </div>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">APTER RATING</div>
        <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
          <AlertCircle size={14} />
          {error || "Rating unavailable"}
        </div>
      </section>
    );
  }

  const components = [
    { label: "Growth", ...data.components.growth },
    { label: "Profitability", ...data.components.profitability },
    { label: "Balance Sheet", ...data.components.balance_sheet },
    { label: "Momentum", ...data.components.momentum },
    { label: "Risk", ...data.components.risk },
  ];

  return (
    <section className="bt-panel p-4 space-y-3">
      <div className="bt-panel-title">APTER RATING</div>

      {/* Headline score */}
      <div className="flex items-center gap-3">
        <div className={`text-4xl font-semibold font-mono ${ratingColor(data.rating)}`}>
          {data.rating.toFixed(1)}
        </div>
        <div>
          <div className="text-sm font-medium">{data.band}</div>
          <div className="text-[10px] text-muted-foreground">{data.ticker} composite score</div>
        </div>
      </div>

      {/* Component bars */}
      <div className="space-y-2">
        {components.map((c) => (
          <div key={c.label}>
            <div className="flex items-center justify-between text-[10px] mb-0.5">
              <span className="text-muted-foreground">{c.label} ({(c.weight * 100).toFixed(0)}%)</span>
              <span className="font-mono font-medium">{c.score.toFixed(1)}</span>
            </div>
            <div className="h-1.5 bg-panel rounded-full overflow-hidden">
              <div
                className="h-full bg-foreground/30 rounded-full transition-all"
                style={{ width: `${(c.score / 10) * 100}%` }}
              />
            </div>
            {c.drivers?.length > 0 && (
              <div className="mt-0.5 text-[10px] text-muted-foreground/70">
                {c.drivers.join(" | ")}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Disclaimer */}
      <div className="pt-2 border-t border-border">
        <p className="text-[10px] text-muted-foreground/60">{COMPLIANCE.APTER_RATING_DISCLAIMER}</p>
      </div>
    </section>
  );
}

/* ─── Live Quote Hook + Card ─── */

function useMarketQuote(ticker: string) {
  const [quote, setQuote] = useState<NormalizedQuote | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    let canceled = false;
    setLoading(true);
    setError(null);

    fetch(`/api/market/quote?symbol=${encodeURIComponent(ticker)}`, { cache: "no-store" })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data?.error ?? "Quote failed");
        if (!canceled) setQuote(data as NormalizedQuote);
      })
      .catch((err) => {
        if (!canceled) setError(err instanceof Error ? err.message : "Quote failed");
      })
      .finally(() => {
        if (!canceled) setLoading(false);
      });

    return () => { canceled = true; };
  }, [ticker]);

  return { quote, loading, error };
}

function formatAsOfTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "\u2014";
  }
}

function LiveQuoteCard({ quote, loading, error }: { quote: NormalizedQuote | null; loading: boolean; error: string | null }) {
  if (loading) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">LIVE QUOTE</div>
        <div className="mt-4 flex items-center justify-center gap-2 py-4 text-muted-foreground text-sm">
          <Loader2 size={14} className="animate-spin" />
          Loading quote...
        </div>
      </section>
    );
  }

  if (error || !quote) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">LIVE QUOTE</div>
        <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
          <AlertCircle size={14} />
          {error || "Quote unavailable"}
        </div>
      </section>
    );
  }

  const rows: Array<{ label: string; value: string }> = [];
  if (quote.open != null) rows.push({ label: "Open", value: formatCurrency(quote.open) });
  if (quote.high != null) rows.push({ label: "High", value: formatCurrency(quote.high) });
  if (quote.low != null) rows.push({ label: "Low", value: formatCurrency(quote.low) });
  if (quote.prevClose != null) rows.push({ label: "Prev Close", value: formatCurrency(quote.prevClose) });

  return (
    <section className="bt-panel p-4">
      <div className="flex items-center justify-between">
        <div className="bt-panel-title">LIVE QUOTE</div>
        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-risk-on animate-pulse" />
          {quote.source}
          {quote.isDelayed && " (Delayed)"}
        </div>
      </div>
      <div className="mt-3 space-y-2">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">{r.label}</span>
            <span className="font-mono">{r.value}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 pt-2 border-t border-border flex items-center gap-1.5 text-[10px] text-muted-foreground">
        <Clock size={10} />
        As of {formatAsOfTime(quote.asOf)}
      </div>
    </section>
  );
}

/* ─── Main StockDetailView ─── */

export function StockDetailView({ ticker }: { ticker: string }) {
  const stock = useMemo(() => getStockDetail(ticker), [ticker]);
  const [range, setRange] = useState<TimeRange>("1M");
  const { quote, loading: quoteLoading, error: quoteError } = useMarketQuote(ticker);

  // Fetch snapshot data from backend (for fundamentals panel)
  const [snapshot, setSnapshot] = useState<StockSnapshot | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(true);

  useEffect(() => {
    if (!ticker) return;
    setSnapshotLoading(true);

    fetchStockSnapshot(ticker).then((res) => {
      if (res.ok) {
        setSnapshot(res.data);
      }
      setSnapshotLoading(false);
    });
  }, [ticker]);

  // Use live quote when available, fall back to mock data
  const price = quote?.price ?? stock.price;
  const change = quote?.change ?? stock.change;
  const changePct = quote?.changePercent ?? stock.changePct;
  const displayMarketCap = snapshot?.quote.market_cap ?? null;

  const changeColor = change >= 0 ? "text-risk-on" : "text-risk-off";
  const changeSign = change >= 0 ? "+" : "";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link href="/dashboard" className="mt-1 text-muted-foreground hover:text-foreground">
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{stock.ticker}</h1>
            <GradeBadge grade={stock.grade} />
          </div>
          <div className="text-muted-foreground text-sm">
            {snapshot?.profile.name ?? stock.companyName} &middot; {snapshot?.profile.sector ?? stock.sector}
            {displayMarketCap !== null && (
              <> &middot; Mkt Cap: {formatMarketCap(displayMarketCap)}</>
            )}
          </div>
          {price > 0 && (
            <div className="mt-1 flex items-baseline gap-2 flex-wrap">
              <span className="text-3xl font-semibold font-mono">{formatCurrency(price)}</span>
              <span className={`text-lg font-mono ${changeColor}`}>
                {changeSign}{formatCurrency(change)} ({changeSign}{changePct.toFixed(2)}%)
              </span>
              {quoteLoading && (
                <Loader2 size={14} className="animate-spin text-muted-foreground" />
              )}
              {quote?.isDelayed && !quoteLoading && (
                <span className="text-[10px] text-muted-foreground bg-white/5 border border-white/10 rounded px-1.5 py-0.5">
                  Delayed
                </span>
              )}
            </div>
          )}
          {quote && (
            <div className="mt-0.5 text-[10px] text-muted-foreground flex items-center gap-1.5">
              <Clock size={10} />
              As of {formatAsOfTime(quote.asOf)} &middot; {quote.source}
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        {/* Left column */}
        <div className="lg:col-span-8 space-y-4">
          {/* Price chart */}
          <section className="bt-panel p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="bt-panel-title">PRICE CHART</div>
              <div className="flex gap-1">
                {TIME_RANGES.map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRange(r)}
                    className={[
                      "h-6 px-2 rounded text-[10px] font-semibold border",
                      range === r
                        ? "bg-muted border-border text-foreground"
                        : "border-transparent text-muted-foreground hover:text-foreground",
                    ].join(" ")}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>
            <PriceChart ticker={ticker} range={range} />
          </section>

          {/* Candlestick chart — Finnhub-powered OHLCV */}
          <CandlestickChart ticker={ticker} />

          {/* Fundamentals & Metrics panel (from snapshot) */}
          {snapshotLoading ? (
            <section className="bt-panel p-4">
              <div className="bt-panel-title">FUNDAMENTALS &amp; METRICS</div>
              <div className="mt-4 flex items-center justify-center gap-2 py-8 text-muted-foreground text-sm">
                <Loader2 size={14} className="animate-spin" />
                Loading fundamentals...
              </div>
            </section>
          ) : snapshot ? (
            <FundamentalsPanel snapshot={snapshot} />
          ) : null}

          {/* Finnhub-grounded AI brief */}
          <GroundedBriefPanel ticker={ticker} />

          {/* Decision Support */}
          <section className="bt-panel p-4">
            <div className="bt-panel-title">DECISION SUPPORT DATA</div>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {(Object.values(stock.decisionSupport) as Array<{ label: string; value: string; description: string }>).map((ds) => (
                <div key={ds.label} className="rounded-md border border-border bg-panel-2 p-3">
                  <div className="flex items-center justify-between">
                    <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{ds.label}</div>
                    <span className="bt-chip border-border text-foreground">
                      <span className="font-semibold">{ds.value}</span>
                    </span>
                  </div>
                  <div className="mt-2 text-xs text-muted-foreground leading-relaxed">{ds.description}</div>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Right column */}
        <div className="lg:col-span-4 space-y-4">
          {/* Live Quote — from normalized market API */}
          <LiveQuoteCard quote={quote} loading={quoteLoading} error={quoteError} />

          {/* Apter Rating — new quantitative composite */}
          <AptRatingCard ticker={ticker} />

          {/* Conviction Score — fetched from backend */}
          <ConvictionScoreCard ticker={ticker} />

          {/* News (from local stock data as fallback) */}
          <section className="bt-panel p-4">
            <div className="bt-panel-title">NEWS</div>
            <div className="mt-3 space-y-3">
              {stock.newsItems.length === 0 ? (
                <div className="text-sm text-muted-foreground">No recent news available.</div>
              ) : (
                stock.newsItems.map((n, i) => {
                  const sentColor =
                    n.sentiment === "positive" ? "text-risk-on" :
                    n.sentiment === "negative" ? "text-risk-off" :
                    "text-muted-foreground";

                  return (
                    <div key={i} className="border-b border-border pb-2 last:border-0 last:pb-0">
                      <div className="text-sm leading-snug">{n.headline}</div>
                      <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                        <span>{n.source}</span>
                        <span>&middot;</span>
                        <span>{n.timestamp}</span>
                        <span>&middot;</span>
                        <span className={sentColor}>{n.sentiment}</span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
