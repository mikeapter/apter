"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  LineChart,
  Line,
  Legend,
} from "recharts";
import { AlertTriangle, Info, Database } from "lucide-react";
import { ClientOnly } from "../../components/ClientOnly";
import { COMPLIANCE } from "../../lib/compliance";
import backtestData from "../../data/pilot_backtest.json";

/* ------------------------------------------------------------------ */
/*  Derived chart data                                                 */
/* ------------------------------------------------------------------ */

const bucketChartData = backtestData.buckets.map((b) => ({
  name: b.label,
  "Mean Return %": b.mean_return_pct,
  "Win Rate %": b.win_rate_pct,
  signals: b.signal_count,
}));

const cumulativeData = backtestData.cumulative_monthly.map((d) => ({
  month: d.month.slice(5), // "06", "07" etc.
  "Top Quintile": d.top,
  "Bottom Quintile": d.bottom,
  "S&P 500": d.benchmark,
}));

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function pct(v: number): string {
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

function colorForReturn(v: number): string {
  if (v > 0) return "text-risk-on";
  if (v < 0) return "text-risk-off";
  return "text-muted-foreground";
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function PerformancePage() {
  const { meta, buckets, quintile_spread } = backtestData;

  const totalSignals = useMemo(
    () => buckets.reduce((s, b) => s + b.signal_count, 0),
    [buckets]
  );

  return (
    <div className="max-w-5xl mx-auto px-4 py-10 space-y-8">
      {/* ── Disclaimer banner ── */}
      <div className="rounded-md border border-risk-neutral/40 bg-risk-neutral/5 p-4 flex gap-3">
        <AlertTriangle
          size={18}
          className="text-risk-neutral flex-shrink-0 mt-0.5"
        />
        <div className="text-sm text-risk-neutral leading-relaxed">
          <span className="font-semibold">Important:</span>{" "}
          {COMPLIANCE.BACKTEST_DISCLAIMER} All results shown are from a pilot
          backtest on a limited sample and should not be extrapolated as
          indicative of future performance. This is not investment advice.
        </div>
      </div>

      {/* ── Header ── */}
      <div>
        <h1 className="text-2xl font-semibold">Model Performance</h1>
        <p className="text-muted-foreground mt-1">
          How Apter signal grades have corresponded to subsequent returns in a
          limited pilot backtest.
        </p>
      </div>

      {/* ── Data source banner ── */}
      <div className="rounded-md border border-border bg-panel-2 p-4 flex gap-3">
        <Database size={16} className="text-muted-foreground flex-shrink-0 mt-0.5" />
        <div className="text-xs text-muted-foreground leading-relaxed space-y-1">
          <div className="font-semibold text-foreground text-sm">Data Sources</div>
          {meta.data_sources.map((src, i) => (
            <div key={i}>• {src}</div>
          ))}
          <div className="mt-1">
            Universe: {meta.universe} · Period: {meta.date_range} ·
            Generated: {meta.generated}
          </div>
        </div>
      </div>

      {/* ── Summary cards ── */}
      <div className="grid gap-3 sm:grid-cols-4">
        <div className="bt-panel p-4">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            Total Signals
          </div>
          <div className="mt-1 text-xl font-semibold font-mono">
            {totalSignals.toLocaleString()}
          </div>
        </div>
        <div className="bt-panel p-4">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            Date Range
          </div>
          <div className="mt-1 text-sm font-semibold">{meta.date_range}</div>
        </div>
        <div className="bt-panel p-4">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            Top–Bottom Spread
          </div>
          <div className="mt-1 text-xl font-semibold font-mono text-risk-on">
            {pct(quintile_spread.spread_pct)}
          </div>
        </div>
        <div className="bt-panel p-4">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            Return Horizon
          </div>
          <div className="mt-1 text-sm font-semibold">{meta.rebalance}</div>
        </div>
      </div>

      {/* ── Pilot label ── */}
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-sm border border-risk-neutral/40 bg-risk-neutral/5 px-2.5 py-1 text-[11px] font-semibold text-risk-neutral">
          <Info size={12} />
          Pilot backtest (limited sample)
        </span>
      </div>

      {/* ── Bar chart: mean return by bucket ── */}
      <section className="bt-panel p-4">
        <div className="bt-panel-title mb-4">
          MEAN 5-DAY RETURN BY SIGNAL GRADE
        </div>
        <div className="h-72">
          <ClientOnly
            fallback={
              <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                Loading chart…
              </div>
            }
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={bucketChartData}
                margin={{ top: 4, right: 16, bottom: 0, left: 0 }}
              >
                <CartesianGrid
                  stroke="hsl(var(--border))"
                  strokeDasharray="3 3"
                  vertical={false}
                />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: number) => `${v}%`}
                  width={48}
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 4,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "hsl(var(--muted-foreground))" }}
                  formatter={(value: number, name: string) => [
                    `${value.toFixed(2)}%`,
                    name,
                  ]}
                />
                <Bar
                  dataKey="Mean Return %"
                  radius={[3, 3, 0, 0]}
                  fill="hsl(var(--risk-on))"
                />
              </BarChart>
            </ResponsiveContainer>
          </ClientOnly>
        </div>
      </section>

      {/* ── Cumulative return chart: top vs bottom quintile ── */}
      <section className="bt-panel p-4">
        <div className="bt-panel-title mb-4">
          CUMULATIVE RETURN — TOP VS BOTTOM QUINTILE
        </div>
        <div className="h-72">
          <ClientOnly
            fallback={
              <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                Loading chart…
              </div>
            }
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={cumulativeData}
                margin={{ top: 4, right: 16, bottom: 0, left: 0 }}
              >
                <CartesianGrid
                  stroke="hsl(var(--border))"
                  strokeDasharray="3 3"
                  vertical={false}
                />
                <XAxis
                  dataKey="month"
                  tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v: number) => `${v}%`}
                  width={48}
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 4,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "hsl(var(--muted-foreground))" }}
                  formatter={(value: number, name: string) => [
                    `${value.toFixed(1)}%`,
                    name,
                  ]}
                />
                <Legend
                  wrapperStyle={{ fontSize: 11 }}
                  iconSize={10}
                />
                <Line
                  type="monotone"
                  dataKey="Top Quintile"
                  stroke="hsl(var(--risk-on))"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="Bottom Quintile"
                  stroke="hsl(var(--risk-off))"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="S&P 500"
                  stroke="hsl(var(--muted-foreground))"
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </ClientOnly>
        </div>
        <p className="text-[11px] text-muted-foreground mt-3">
          Cumulative returns are hypothetical and assume weekly equal-weight
          rebalancing with no transaction costs or slippage.
        </p>
      </section>

      {/* ── Results table ── */}
      <section className="bt-panel overflow-hidden">
        <div className="bt-panel-title px-4 pt-4 mb-3">
          BUCKET BREAKDOWN
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-panel-2">
              <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                <th className="text-left px-4 py-2.5 font-medium">Bucket</th>
                <th className="text-left px-4 py-2.5 font-medium">
                  Grade Range
                </th>
                <th className="text-right px-4 py-2.5 font-medium">Signals</th>
                <th className="text-right px-4 py-2.5 font-medium">
                  Mean Return
                </th>
                <th className="text-right px-4 py-2.5 font-medium">
                  Median Return
                </th>
                <th className="text-right px-4 py-2.5 font-medium">
                  Win Rate
                </th>
                <th className="text-right px-4 py-2.5 font-medium">Worst</th>
                <th className="text-right px-4 py-2.5 font-medium">Best</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {buckets.map((b) => (
                <tr
                  key={b.label}
                  className="hover:bg-muted/30 transition-colors"
                >
                  <td className="px-4 py-3 font-medium">{b.label}</td>
                  <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                    {b.grade_range}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {b.signal_count}
                  </td>
                  <td
                    className={`px-4 py-3 text-right font-mono font-semibold ${colorForReturn(b.mean_return_pct)}`}
                  >
                    {pct(b.mean_return_pct)}
                  </td>
                  <td
                    className={`px-4 py-3 text-right font-mono ${colorForReturn(b.median_return_pct)}`}
                  >
                    {pct(b.median_return_pct)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {b.win_rate_pct.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-risk-off">
                    {pct(b.worst_pct)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-risk-on">
                    {pct(b.best_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* ── Quintile spread callout ── */}
      <div className="bt-panel p-4">
        <div className="bt-panel-title mb-2">QUINTILE SPREAD</div>
        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Top Quintile (9–10) Mean
            </div>
            <div className="mt-0.5 font-mono font-semibold text-risk-on">
              {pct(quintile_spread.top_quintile_mean_pct)}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Bottom Quintile (1–2) Mean
            </div>
            <div className="mt-0.5 font-mono font-semibold text-risk-off">
              {pct(quintile_spread.bottom_quintile_mean_pct)}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              Spread
            </div>
            <div className="mt-0.5 font-mono font-semibold text-foreground">
              {pct(quintile_spread.spread_pct)}
            </div>
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground mt-3">
          {quintile_spread.description}
        </p>
      </div>

      {/* ── Methodology ── */}
      <section className="bt-panel p-4 space-y-4">
        <div className="bt-panel-title">METHODOLOGY & ASSUMPTIONS</div>

        <div className="space-y-3 text-sm text-muted-foreground leading-relaxed">
          <div>
            <span className="text-foreground font-medium">Universe: </span>
            {meta.universe}. Stocks that were delisted or had insufficient
            liquidity during the test period were excluded.
          </div>

          <div>
            <span className="text-foreground font-medium">
              Signal generation:{" "}
            </span>
            Apter&apos;s multi-factor scoring engine assigns each stock a grade
            from 1 (strong bearish) to 10 (strong bullish) based on technical,
            breadth, and regime inputs. Grades are generated at end-of-day.
          </div>

          <div>
            <span className="text-foreground font-medium">
              Return calculation:{" "}
            </span>
            Forward 5-day returns are measured from the close of the signal date
            to the close 5 trading days later, using adjusted close prices.
          </div>

          <div>
            <span className="text-foreground font-medium">
              Rebalancing:{" "}
            </span>
            {meta.rebalance}. No transaction costs, slippage, or taxes are
            included. Real-world execution would reduce returns.
          </div>

          <div>
            <span className="text-foreground font-medium">
              Survivorship bias:{" "}
            </span>
            The universe is based on current S&amp;P 500 constituents, which
            introduces survivorship bias. Stocks that were removed from the index
            during the period are not included.
          </div>

          <div>
            <span className="text-foreground font-medium">
              Look-ahead bias:{" "}
            </span>
            Signals use only data available at the close of the signal date. No
            future information is used in grade calculation.
          </div>

          <div>
            <span className="text-foreground font-medium">
              Sample limitation:{" "}
            </span>
            This is a pilot backtest covering a single 19-month period.
            Statistical significance varies by bucket. Results from a single
            period may not generalize.
          </div>
        </div>
      </section>

      {/* ── Bottom disclaimer ── */}
      <div className="rounded-md border border-border bg-panel-2 p-4 space-y-2">
        <div className="text-xs font-semibold text-foreground">Disclosures</div>
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          {COMPLIANCE.BACKTEST_DISCLAIMER}
        </p>
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          {COMPLIANCE.NOT_INVESTMENT_ADVICE}
        </p>
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Hypothetical performance results have many inherent limitations. No
          representation is being made that any account will or is likely to
          achieve profits or losses similar to those shown. There are frequently
          sharp differences between hypothetical performance results and the
          actual results subsequently achieved by any particular trading program.
        </p>
      </div>
    </div>
  );
}
