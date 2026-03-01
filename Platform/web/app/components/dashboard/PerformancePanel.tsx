"use client";

import { useMemo, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import type { TimeRange } from "../../lib/dashboard";
import { generatePerformanceData } from "../../lib/dashboard";
import { usePortfolio } from "../../providers/PortfolioProvider";
import { ClientOnly } from "../ClientOnly";
import { useAuth } from "../../hooks/useAuth";
import { LockedPanel } from "../billing/LockedPanel";
import { TierBadge } from "../billing/TierBadge";

const TIME_RANGES: TimeRange[] = ["1D", "1W", "1M", "3M", "1Y", "ALL"];
const PRO_RANGES: Set<TimeRange> = new Set(["1Y", "ALL"]);

function formatValue(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}

export function PerformancePanel() {
  const [range, setRange] = useState<TimeRange>("1M");
  const { holdings, totalValue } = usePortfolio();
  const { user } = useAuth();

  const userTier = user?.tier ?? "observer";
  const isPro = userTier === "pro";

  const data = useMemo(() => generatePerformanceData(range), [range]);

  const hasHoldings = holdings.length > 0;

  // If user selected a pro-gated range but isn't pro, show locked state
  const isRangeLocked = PRO_RANGES.has(range) && !isPro;

  return (
    <section className="bt-panel p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="bt-panel-title">PERFORMANCE</div>
        <div className="flex gap-1">
          {TIME_RANGES.map((r) => {
            const locked = PRO_RANGES.has(r) && !isPro;
            return (
              <button
                key={r}
                type="button"
                onClick={() => setRange(r)}
                className={[
                  "h-6 px-2 rounded text-[10px] font-semibold border",
                  range === r
                    ? "bg-muted border-border text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground",
                  locked ? "opacity-60" : "",
                ].join(" ")}
                title={locked ? "Upgrade to Pro for extended history" : undefined}
              >
                {r}
                {locked && <span className="ml-0.5 text-[8px] align-super">*</span>}
              </button>
            );
          })}
        </div>
      </div>

      {/* Pro badge for extended ranges */}
      {isRangeLocked && (
        <div className="flex items-center gap-2 mb-2">
          <TierBadge tier="pro" />
          <span className="text-[10px] text-muted-foreground">Extended history requires Pro</span>
        </div>
      )}

      {/* Portfolio summary line */}
      {hasHoldings && !isRangeLocked && (
        <div className="text-sm mb-2">
          <span className="text-muted-foreground">Portfolio Value: </span>
          <span className="font-semibold font-mono">{formatValue(totalValue)}</span>
        </div>
      )}

      <div className="flex-1 min-h-[200px]">
        {isRangeLocked ? (
          <div className="h-full flex items-center justify-center">
            <LockedPanel
              requiredTier="pro"
              title="Extended Performance History"
              benefits={["Full 1-year and all-time performance charts", "Long-term trend analysis and drawdown visibility"]}
            />
          </div>
        ) : (
          <ClientOnly fallback={<div className="h-full flex items-center justify-center text-muted-foreground text-sm">Loading chart...</div>}>
            {!hasHoldings ? (
              <div className="h-full flex items-center justify-center text-muted-foreground text-sm">
                Add holdings to see performance tracking
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <defs>
                    <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
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
                    tickFormatter={formatValue}
                    width={60}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 4,
                      fontSize: 12,
                    }}
                    labelStyle={{ color: "hsl(var(--muted-foreground))" }}
                  />
                  <Area
                    type="monotone"
                    dataKey="portfolio"
                    stroke="hsl(var(--risk-on))"
                    fill="url(#portfolioGrad)"
                    strokeWidth={1.5}
                    name="Portfolio"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </ClientOnly>
        )}
      </div>
    </section>
  );
}
