"use client";

import { useMemo, useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Loader2,
  AlertCircle,
  AlertTriangle,
  Info,
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
import { authGet } from "@/lib/fetchWithAuth";
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

type TimeRange = "1D" | "1W" | "1M" | "3M" | "1Y" | "ALL";
const TIME_RANGES: TimeRange[] = ["1D", "1W", "1M", "3M", "1Y", "ALL"];

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

function formatMarketCap(n: number | null): string {
  if (n === null || n === undefined) return "N/A";
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`;
  return `$${n.toLocaleString()}`;
}

function PriceChart({
  ticker,
  range,
}: {
  ticker: string;
  range: TimeRange;
}) {
  const data = useMemo(
    () => generateStockChartData(ticker, range),
    [ticker, range]
  );

  return (
    <ClientOnly
      fallback={
        <div className="h-[250px] flex items-center justify-center text-muted-foreground text-sm">
          Loading chart...
        </div>
      }
    >
      <ResponsiveContainer width="100%" height={250}>
        <AreaChart
          data={data}
          margin={{ top: 4, right: 4, bottom: 0, left: 0 }}
        >
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="0%"
                stopColor="hsl(var(--risk-on))"
                stopOpacity={0.3}
              />
              <stop
                offset="100%"
                stopColor="hsl(var(--risk-on))"
                stopOpacity={0}
              />
            </linearGradient>
          </defs>
          <CartesianGrid
            stroke="hsl(var(--border))"
            strokeDasharray="3 3"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={{
              fontSize: 10,
              fill: "hsl(var(--muted-foreground))",
            }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{
              fontSize: 10,
              fill: "hsl(var(--muted-foreground))",
            }}
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
  const cls =
    colorMap[label] ||
    "bg-muted/50 text-muted-foreground border-border";
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase tracking-wider border ${cls}`}
    >
      {label}
    </span>
  );
}

/* ─── Metric row component ─── */

function MetricRow({
  name,
  metric,
  unit = "",
}: {
  name: string;
  metric: MetricValue;
  unit?: "x" | "%" | "";
}) {
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
        <span>
          Data as of: {formatDataAsOf(dataAsOf)}
        </span>
        <span>&middot;</span>
        <span>
          Fetched: {formatFetchedAt(fetchedAt)}
        </span>
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
          <MetricRow
            name="Operating Margin"
            metric={f.operating_margin_ttm}
            unit="%"
          />
          <MetricRow name="ROE" metric={f.roe_ttm} unit="%" />
        </div>

        {/* Risk & Balance Sheet */}
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
            Risk &amp; Balance Sheet
          </div>
          <MetricRow
            name="Debt/Equity"
            metric={f.debt_to_equity_mrq}
            unit="x"
          />
          <MetricRow name="Beta" metric={f.beta} unit="" />
          <MetricRow
            name="30d Volatility"
            metric={f.realized_vol_30d}
            unit="%"
          />
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
  news: {
    headline: string;
    source: string;
    published_at: string;
    impact: string;
  }[];
  what_to_watch: string[];
  data_quality?: {
    stale_flags: string[];
    missing_fields: string[];
    provider: string;
    last_updated: string;
  };
  staleness_notice?: string | null;
  data_as_of?: string | null;
  source?: string;
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

    authGet<AIOverview>(
      `/api/stocks/${encodeURIComponent(ticker)}/ai-overview`
    ).then((res) => {
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
  const perfEntries = Object.entries(perf).filter(
    ([, v]) => v !== null
  ) as [string, number][];

  return (
    <section className="bt-panel p-4 space-y-4">
      <div className="bt-panel-title">AI PERFORMANCE OVERVIEW</div>

      {/* Staleness warning */}
      {data.staleness_notice && (
        <div className="flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2">
          <AlertTriangle
            size={12}
            className="text-amber-400 mt-0.5 shrink-0"
          />
          <p className="text-[11px] text-amber-400 leading-relaxed">
            {data.staleness_notice}
          </p>
        </div>
      )}

      {/* Snapshot */}
      <p className="text-sm text-muted-foreground leading-relaxed">
        {data.ticker} is trading at {formatCurrency(data.snapshot.price)},{" "}
        <span
          className={
            data.snapshot.day_change_pct >= 0
              ? "text-risk-on"
              : "text-risk-off"
          }
        >
          {data.snapshot.day_change_pct >= 0 ? "+" : ""}
          {data.snapshot.day_change_pct.toFixed(2)}%
        </span>{" "}
        today.
      </p>

      {/* Performance windows */}
      {perfEntries.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
            Performance
          </div>
          <div className="flex flex-wrap gap-3">
            {perfEntries.map(([k, v]) => (
              <div
                key={k}
                className="rounded-md border border-border bg-panel-2 px-2.5 py-1.5 text-center"
              >
                <div className="text-[9px] uppercase tracking-[0.14em] text-muted-foreground">
                  {k}
                </div>
                <div
                  className={`text-sm font-mono font-medium ${v >= 0 ? "text-risk-on" : "text-risk-off"}`}
                >
                  {v >= 0 ? "+" : ""}
                  {v.toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Drivers */}
      {data.drivers.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
            Key Drivers
          </div>
          <ul className="space-y-1.5">
            {data.drivers.map((d, i) => (
              <li
                key={i}
                className="flex items-start gap-2 text-xs text-muted-foreground"
              >
                <TrendingUp
                  size={12}
                  className="text-risk-on mt-0.5 shrink-0"
                />
                {d}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Outlook */}
      <div>
        <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
          Outlook
        </div>
        <div className="space-y-2">
          <div className="rounded-md border border-border bg-panel-2 px-3 py-2">
            <div className="flex items-center gap-2 text-[10px] text-muted-foreground mb-1">
              <span className="font-semibold">BASE</span>
              <span className="ml-auto">
                {data.outlook.probabilities.base}%
              </span>
            </div>
            <p className="text-xs leading-relaxed">
              {data.outlook.base_case}
            </p>
          </div>
          <div className="rounded-md border border-risk-on/20 bg-risk-on/5 px-3 py-2">
            <div className="flex items-center gap-2 text-[10px] text-risk-on mb-1">
              <TrendingUp size={10} />
              <span className="font-semibold">BULL</span>
              <span className="ml-auto">
                {data.outlook.probabilities.bull}%
              </span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {data.outlook.bull_case}
            </p>
          </div>
          <div className="rounded-md border border-risk-off/20 bg-risk-off/5 px-3 py-2">
            <div className="flex items-center gap-2 text-[10px] text-risk-off mb-1">
              <TrendingDown size={10} />
              <span className="font-semibold">BEAR</span>
              <span className="ml-auto">
                {data.outlook.probabilities.bear}%
              </span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {data.outlook.bear_case}
            </p>
          </div>
        </div>
      </div>

      {/* News */}
      {data.news.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
            Recent News
          </div>
          <div className="space-y-2">
            {data.news.map((n, i) => (
              <div
                key={i}
                className="border-b border-border pb-2 last:border-0 last:pb-0"
              >
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
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
            What to Watch
          </div>
          <ul className="space-y-1">
            {data.what_to_watch.map((w, i) => (
              <li key={i} className="text-xs text-muted-foreground">
                &bull; {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Data source + Disclaimer */}
      <div className="text-[10px] text-muted-foreground pt-2 border-t border-border space-y-1">
        {data.data_as_of && (
          <div>
            Data as of: {formatDataAsOf(data.data_as_of)}
            {data.source && <> &middot; Source: {data.source}</>}
          </div>
        )}
        <div>{COMPLIANCE.NOT_INVESTMENT_ADVICE}</div>
      </div>
    </section>
  );
}

export function StockDetailView({ ticker }: { ticker: string }) {
  const stock = useMemo(() => getStockDetail(ticker), [ticker]);
  const [range, setRange] = useState<TimeRange>("1M");

  // Fetch snapshot data from backend
  const [snapshot, setSnapshot] = useState<StockSnapshot | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(true);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    setSnapshotLoading(true);
    setSnapshotError(null);

    fetchStockSnapshot(ticker).then((res) => {
      if (res.ok) {
        setSnapshot(res.data);
      } else {
        setSnapshotError(res.error || "Failed to load snapshot");
      }
      setSnapshotLoading(false);
    });
  }, [ticker]);

  // Use snapshot data for price if available, otherwise fall back to local
  const displayPrice = snapshot?.quote.price ?? stock.price;
  const displayChange = snapshot?.quote.change ?? stock.change;
  const displayChangePct = snapshot?.quote.change_pct ?? stock.changePct;
  const displayName = snapshot?.profile.name ?? stock.companyName;
  const displaySector = snapshot?.profile.sector ?? stock.sector;
  const displayMarketCap = snapshot?.quote.market_cap ?? null;

  const changeColor = displayChange >= 0 ? "text-risk-on" : "text-risk-off";
  const changeSign = displayChange >= 0 ? "+" : "";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link
          href="/dashboard"
          className="mt-1 text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{stock.ticker}</h1>
            <GradeBadge grade={stock.grade} />
          </div>
          <div className="text-muted-foreground text-sm">
            {displayName} &middot; {displaySector}
            {displayMarketCap !== null && (
              <> &middot; Mkt Cap: {formatMarketCap(displayMarketCap)}</>
            )}
          </div>
          {displayPrice > 0 && (
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-3xl font-semibold font-mono">
                {formatCurrency(displayPrice)}
              </span>
              <span className={`text-lg font-mono ${changeColor}`}>
                {changeSign}
                {formatCurrency(displayChange)} ({changeSign}
                {displayChangePct.toFixed(2)}%)
              </span>
            </div>
          )}
          {/* Quote source line */}
          {snapshot && (
            <div className="mt-1 text-[10px] text-muted-foreground">
              Source: {snapshot.quote.source} &middot; Session:{" "}
              {snapshot.quote.session}
              {snapshot.quote.delay_seconds > 0 && (
                <> &middot; Delayed {snapshot.quote.delay_seconds}s</>
              )}
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

          {/* Fundamentals & Metrics panel (from snapshot) */}
          {snapshotLoading ? (
            <section className="bt-panel p-4">
              <div className="bt-panel-title">
                FUNDAMENTALS &amp; METRICS
              </div>
              <div className="mt-4 flex items-center justify-center gap-2 py-8 text-muted-foreground text-sm">
                <Loader2 size={14} className="animate-spin" />
                Loading fundamentals...
              </div>
            </section>
          ) : snapshotError || !snapshot ? (
            <section className="bt-panel p-4">
              <div className="bt-panel-title">
                FUNDAMENTALS &amp; METRICS
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
                <AlertCircle size={14} />
                {snapshotError || "Fundamentals unavailable"}
              </div>
            </section>
          ) : (
            <FundamentalsPanel snapshot={snapshot} />
          )}

          {/* AI Overview — fetched from backend */}
          <AIOverviewPanel ticker={ticker} />
        </div>

        {/* Right column */}
        <div className="lg:col-span-4 space-y-4">
          {/* Conviction Score — fetched from backend */}
          <ConvictionScoreCard ticker={ticker} />

          {/* News (from local stock data as fallback) */}
          <section className="bt-panel p-4">
            <div className="bt-panel-title">NEWS</div>
            <div className="mt-3 space-y-3">
              {stock.newsItems.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No recent news available.
                </div>
              ) : (
                stock.newsItems.map((n, i) => {
                  const sentColor =
                    n.sentiment === "positive"
                      ? "text-risk-on"
                      : n.sentiment === "negative"
                        ? "text-risk-off"
                        : "text-muted-foreground";

                  return (
                    <div
                      key={i}
                      className="border-b border-border pb-2 last:border-0 last:pb-0"
                    >
                      <div className="text-sm leading-snug">
                        {n.headline}
                      </div>
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
