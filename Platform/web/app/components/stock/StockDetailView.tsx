"use client";

import { useMemo, useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, TrendingUp, TrendingDown, Loader2, AlertCircle } from "lucide-react";
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
import { QuoteBox } from "./QuoteBox";
import { CandlestickChart } from "./CandlestickChart";
import { authGet } from "@/lib/fetchWithAuth";
import { COMPLIANCE } from "../../lib/compliance";
import { FeatureGate } from "../billing/FeatureGate";
import { TierBadge } from "../billing/TierBadge";

type TimeRange = "1D" | "1W" | "1M" | "3M" | "1Y" | "ALL";
const TIME_RANGES: TimeRange[] = ["1D", "1W", "1M", "3M", "1Y", "ALL"];

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

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

/* ─── AI Overview types ─── */
type AIOverview = {
  ticker: string;
  as_of: string;
  snapshot: { price: number; day_change_pct: number; volume: number | null };
  performance: Record<string, number | null>;
  drivers: string[];
  outlook: {
    base_case: string;
    bull_case: string;
    bear_case: string;
    probabilities: { base: number; bull: number; bear: number };
  };
  news: { headline: string; source: string; published_at: string; impact: string }[];
  what_to_watch: string[];
  disclaimer: string;
};

function impactColor(impact: string) {
  if (impact === "positive") return "text-risk-on";
  if (impact === "negative") return "text-risk-off";
  return "text-muted-foreground";
}

function AIOverviewPanel({ ticker }: { ticker: string }) {
  const [data, setData] = useState<AIOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);

    authGet<AIOverview>(`/api/stocks/${encodeURIComponent(ticker)}/ai-overview`).then((res) => {
      if (res.ok) {
        setData(res.data);
      } else {
        setError(res.error || "Failed to load AI overview");
      }
      setLoading(false);
    });
  }, [ticker]);

  if (loading) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">AI PERFORMANCE OVERVIEW</div>
        <div className="mt-4 flex items-center justify-center gap-2 py-8 text-muted-foreground text-sm">
          <Loader2 size={14} className="animate-spin" />
          Generating analysis...
        </div>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">AI PERFORMANCE OVERVIEW</div>
        <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
          <AlertCircle size={14} />
          {error || "Overview unavailable"}
        </div>
      </section>
    );
  }

  const perf = data.performance;
  const perfEntries = Object.entries(perf).filter(([, v]) => v !== null) as [string, number][];

  return (
    <section className="bt-panel p-4 space-y-4">
      <div className="bt-panel-title">AI PERFORMANCE OVERVIEW</div>

      {/* Snapshot */}
      <p className="text-sm text-muted-foreground leading-relaxed">
        {data.ticker} is trading at {formatCurrency(data.snapshot.price)},{" "}
        <span className={data.snapshot.day_change_pct >= 0 ? "text-risk-on" : "text-risk-off"}>
          {data.snapshot.day_change_pct >= 0 ? "+" : ""}{data.snapshot.day_change_pct.toFixed(2)}%
        </span>{" "}
        today.
      </p>

      {/* Performance windows */}
      {perfEntries.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">Performance</div>
          <div className="flex flex-wrap gap-3">
            {perfEntries.map(([k, v]) => (
              <div key={k} className="rounded-md border border-border bg-panel-2 px-2.5 py-1.5 text-center">
                <div className="text-[9px] uppercase tracking-[0.14em] text-muted-foreground">{k}</div>
                <div className={`text-sm font-mono font-medium ${v >= 0 ? "text-risk-on" : "text-risk-off"}`}>
                  {v >= 0 ? "+" : ""}{v.toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Drivers */}
      {data.drivers.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">Key Drivers</div>
          <ul className="space-y-1.5">
            {data.drivers.map((d, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                <TrendingUp size={12} className="text-risk-on mt-0.5 shrink-0" />
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Outlook — bull/bear narrative gated to Signals+ */}
      <FeatureGate
        requiredTier="signals"
        title="Full Bull/Base/Bear Outlook"
        benefits={["Detailed base, bull, and bear case narratives", "Probability-weighted scenario analysis"]}
      >
        <div>
          <div className="flex items-center gap-2 mb-2">
            <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Outlook</div>
            <TierBadge tier="signals" />
          </div>
          <div className="space-y-2">
            <div className="rounded-md border border-border bg-panel-2 px-3 py-2">
              <div className="flex items-center gap-2 text-[10px] text-muted-foreground mb-1">
                <span className="font-semibold">BASE</span>
                <span className="ml-auto">{data.outlook.probabilities.base}%</span>
              </div>
              <p className="text-xs leading-relaxed">{data.outlook.base_case}</p>
            </div>
            <div className="rounded-md border border-risk-on/20 bg-risk-on/5 px-3 py-2">
              <div className="flex items-center gap-2 text-[10px] text-risk-on mb-1">
                <TrendingUp size={10} />
                <span className="font-semibold">BULL</span>
                <span className="ml-auto">{data.outlook.probabilities.bull}%</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">{data.outlook.bull_case}</p>
            </div>
            <div className="rounded-md border border-risk-off/20 bg-risk-off/5 px-3 py-2">
              <div className="flex items-center gap-2 text-[10px] text-risk-off mb-1">
                <TrendingDown size={10} />
                <span className="font-semibold">BEAR</span>
                <span className="ml-auto">{data.outlook.probabilities.bear}%</span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">{data.outlook.bear_case}</p>
            </div>
          </div>
        </div>
      </FeatureGate>

      {/* News */}
      {data.news.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">Recent News</div>
          <div className="space-y-2">
            {data.news.map((n, i) => (
              <div key={i} className="border-b border-border pb-2 last:border-0 last:pb-0">
                <div className="text-xs leading-snug">{n.headline}</div>
                <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                  <span>{n.source}</span>
                  <span>&middot;</span>
                  <span className={impactColor(n.impact)}>{n.impact}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* What to watch */}
      {data.what_to_watch.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">What to Watch</div>
          <ul className="space-y-1">
            {data.what_to_watch.map((w, i) => (
              <li key={i} className="text-xs text-muted-foreground">• {w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Disclaimer */}
      <div className="text-[10px] text-muted-foreground pt-2 border-t border-border">
        {COMPLIANCE.NOT_INVESTMENT_ADVICE}
      </div>
    </section>
  );
}

export function StockDetailView({ ticker }: { ticker: string }) {
  const stock = useMemo(() => getStockDetail(ticker), [ticker]);
  const [range, setRange] = useState<TimeRange>("1M");

  const changeColor = stock.change >= 0 ? "text-risk-on" : "text-risk-off";
  const changeSign = stock.change >= 0 ? "+" : "";

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
          <div className="text-muted-foreground text-sm">{stock.companyName} &middot; {stock.sector}</div>
          {stock.price > 0 && (
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-3xl font-semibold font-mono">{formatCurrency(stock.price)}</span>
              <span className={`text-lg font-mono ${changeColor}`}>
                {changeSign}{formatCurrency(stock.change)} ({changeSign}{stock.changePct.toFixed(2)}%)
              </span>
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

          {/* AI Overview — fetched from backend */}
          <AIOverviewPanel ticker={ticker} />

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
          {/* Live Quote — Finnhub-powered, auto-refreshes every 15s */}
          <QuoteBox ticker={ticker} />

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
