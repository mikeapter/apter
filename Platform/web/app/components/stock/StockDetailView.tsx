"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  BarChart,
  Bar,
} from "recharts";
import { getStockDetail, generateStockChartData, type StockDetail, type GradeBreakdown } from "../../lib/stockData";
import { GradeBadge } from "../ui/GradeBadge";
import { ClientOnly } from "../ClientOnly";
import { COMPLIANCE } from "../../lib/compliance";

type TimeRange = "1D" | "1W" | "1M" | "3M" | "1Y" | "ALL";
const TIME_RANGES: TimeRange[] = ["1D", "1W", "1M", "3M", "1Y", "ALL"];

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

function GradeBreakdownChart({ breakdown }: { breakdown: GradeBreakdown }) {
  const data = [
    { name: "Momentum", value: breakdown.momentum },
    { name: "Valuation", value: breakdown.valuation },
    { name: "Quality", value: breakdown.quality },
    { name: "Volatility", value: breakdown.volatility },
    { name: "Sentiment", value: breakdown.sentiment },
  ];

  function barColor(val: number): string {
    if (val <= 3) return "hsl(var(--risk-off))";
    if (val <= 7) return "hsl(var(--risk-neutral))";
    return "hsl(var(--risk-on))";
  }

  return (
    <ClientOnly>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 20, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 10]}
            tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            tickLine={false}
            axisLine={false}
            width={80}
          />
          <Tooltip
            contentStyle={{
              background: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 4,
              fontSize: 12,
            }}
          />
          <Bar
            dataKey="value"
            radius={[0, 3, 3, 0]}
            fill="hsl(var(--risk-neutral))"
          >
            {data.map((entry, i) => (
              <rect key={i} fill={barColor(entry.value)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ClientOnly>
  );
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

          {/* AI Overview */}
          <section className="bt-panel p-4">
            <div className="bt-panel-title">AI PERFORMANCE OVERVIEW</div>
            <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
              {stock.aiOverview}
            </p>
            <div className="mt-2 text-[10px] text-muted-foreground">
              {COMPLIANCE.NOT_INVESTMENT_ADVICE}
            </div>
          </section>

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
          {/* Grade breakdown */}
          <section className="bt-panel p-4">
            <div className="bt-panel-title">GRADE BREAKDOWN</div>
            <div className="mt-3">
              <GradeBreakdownChart breakdown={stock.gradeBreakdown} />
            </div>
            <div className="mt-2 text-[10px] text-muted-foreground">
              {COMPLIANCE.GRADE_TOOLTIP}
            </div>
          </section>

          {/* News */}
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
