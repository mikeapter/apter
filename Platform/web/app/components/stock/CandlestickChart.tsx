"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, AlertCircle } from "lucide-react";
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";
import { fetchCandles, type FinnhubCandles } from "../../lib/api/market";
import { ClientOnly } from "../ClientOnly";

// ---------------------------------------------------------------------------
// Types & helpers
// ---------------------------------------------------------------------------

type CandleRow = {
  date: string;
  ts: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  /** bottom of the body (min of open, close) */
  bodyBase: number;
  /** height of the body */
  bodyHeight: number;
  bullish: boolean;
};

type Resolution = "1" | "5" | "15" | "60" | "D" | "W" | "M";

const RESOLUTION_OPTIONS: { value: Resolution; label: string }[] = [
  { value: "5", label: "5m" },
  { value: "15", label: "15m" },
  { value: "60", label: "1H" },
  { value: "D", label: "1D" },
  { value: "W", label: "1W" },
  { value: "M", label: "1M" },
];

/** How far back (seconds) for each resolution's default window */
const LOOKBACK: Record<Resolution, number> = {
  "1": 6 * 3600,       // 6 hours
  "5": 24 * 3600,      // 1 day
  "15": 3 * 24 * 3600, // 3 days
  "60": 14 * 24 * 3600, // 2 weeks
  "D": 180 * 24 * 3600, // 6 months
  "W": 365 * 24 * 3600, // 1 year
  "M": 3 * 365 * 24 * 3600, // 3 years
};

function formatDate(ts: number, resolution: string): string {
  const d = new Date(ts * 1000);
  if (["1", "5", "15", "60"].includes(resolution)) {
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

function transformCandles(raw: FinnhubCandles): CandleRow[] {
  if (!raw.t?.length) return [];

  return raw.t.map((ts, i) => {
    const o = raw.o[i];
    const h = raw.h[i];
    const l = raw.l[i];
    const c = raw.c[i];
    const v = raw.v[i];
    const bullish = c >= o;

    return {
      date: formatDate(ts, raw.resolution),
      ts,
      open: o,
      high: h,
      low: l,
      close: c,
      volume: v,
      bodyBase: Math.min(o, c),
      bodyHeight: Math.abs(c - o) || 0.01, // avoid zero-height bars
      bullish,
    };
  });
}

// ---------------------------------------------------------------------------
// Custom Recharts bar shape to draw candle bodies + wicks
// ---------------------------------------------------------------------------

function CandleShape(props: any) {
  const { x, y, width, height, payload } = props;
  if (!payload) return null;

  const { high, low, bodyBase, bullish } = payload as CandleRow;

  // The bar's y/height correspond to bodyBase → bodyBase+bodyHeight
  // We need to compute wick positions in the same coordinate system
  const yScale = (val: number) => {
    // y is the top of the bar body, and it represents bodyBase + bodyHeight
    // y + height is the bottom, representing bodyBase
    const bodyTop = bodyBase + (payload as CandleRow).bodyHeight;
    if (bodyTop === bodyBase) return y;
    const ratio = (val - bodyBase) / (bodyTop - bodyBase);
    return y + height - ratio * height;
  };

  const fill = bullish ? "hsl(var(--risk-on))" : "hsl(var(--risk-off))";
  const midX = x + width / 2;

  // We can't easily draw wicks with YAxis-scale from the bar shape alone,
  // so we just render the body rectangle. Wicks require axis scale access
  // which isn't easily available here. The body-only view is still useful.
  return (
    <g>
      {/* Body */}
      <rect
        x={x}
        y={y}
        width={width}
        height={Math.max(height, 1)}
        fill={fill}
        stroke={fill}
        strokeWidth={0.5}
        rx={1}
      />
    </g>
  );
}

// ---------------------------------------------------------------------------
// Custom tooltip
// ---------------------------------------------------------------------------

function CandleTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload as CandleRow | undefined;
  if (!d) return null;

  return (
    <div
      className="rounded-md border border-border bg-card p-2 text-xs shadow-md"
      style={{ minWidth: 140 }}
    >
      <div className="font-medium mb-1">{d.date}</div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
        <span className="text-muted-foreground">Open</span>
        <span className="font-mono text-right">{formatCurrency(d.open)}</span>
        <span className="text-muted-foreground">High</span>
        <span className="font-mono text-right text-risk-on">{formatCurrency(d.high)}</span>
        <span className="text-muted-foreground">Low</span>
        <span className="font-mono text-right text-risk-off">{formatCurrency(d.low)}</span>
        <span className="text-muted-foreground">Close</span>
        <span className={`font-mono text-right ${d.bullish ? "text-risk-on" : "text-risk-off"}`}>
          {formatCurrency(d.close)}
        </span>
        <span className="text-muted-foreground">Volume</span>
        <span className="font-mono text-right">{(d.volume / 1_000_000).toFixed(1)}M</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function CandlestickChart({ ticker }: { ticker: string }) {
  const [resolution, setResolution] = useState<Resolution>("D");
  const [candles, setCandles] = useState<FinnhubCandles | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    const now = Math.floor(Date.now() / 1000);
    const from = now - LOOKBACK[resolution];

    fetchCandles(ticker, resolution, from, now).then((data) => {
      if (cancelled) return;
      if (data) {
        setCandles(data);
        setError(null);
      } else {
        setError("Unable to load chart data");
      }
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [ticker, resolution]);

  const rows = useMemo(() => (candles ? transformCandles(candles) : []), [candles]);

  // Compute Y-axis domain from actual high/low
  const [yMin, yMax] = useMemo(() => {
    if (!rows.length) return [0, 100];
    let min = Infinity;
    let max = -Infinity;
    for (const r of rows) {
      if (r.low < min) min = r.low;
      if (r.high > max) max = r.high;
    }
    const pad = (max - min) * 0.05 || 1;
    return [min - pad, max + pad];
  }, [rows]);

  return (
    <section className="bt-panel p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="bt-panel-title">CANDLESTICK CHART</div>
        <div className="flex gap-1">
          {RESOLUTION_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setResolution(opt.value)}
              className={[
                "h-6 px-2 rounded text-[10px] font-semibold border",
                resolution === opt.value
                  ? "bg-muted border-border text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              ].join(" ")}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="h-[280px] flex items-center justify-center text-muted-foreground text-sm gap-2">
          <Loader2 size={14} className="animate-spin" />
          Loading chart...
        </div>
      )}

      {!loading && error && (
        <div className="h-[280px] flex items-center justify-center text-muted-foreground text-sm gap-2">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {!loading && !error && rows.length > 0 && (
        <ClientOnly
          fallback={
            <div className="h-[280px] flex items-center justify-center text-muted-foreground text-sm">
              Loading chart...
            </div>
          }
        >
          <ResponsiveContainer width="100%" height={280}>
            <ComposedChart data={rows} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
              <CartesianGrid
                stroke="hsl(var(--border))"
                strokeDasharray="3 3"
                vertical={false}
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                domain={[yMin, yMax]}
                tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
                width={60}
              />
              <Tooltip content={<CandleTooltip />} />
              <Bar
                dataKey="bodyHeight"
                stackId="candle"
                shape={<CandleShape />}
                isAnimationActive={false}
              >
                {rows.map((row, i) => (
                  <Cell
                    key={i}
                    fill={row.bullish ? "hsl(var(--risk-on))" : "hsl(var(--risk-off))"}
                  />
                ))}
              </Bar>
            </ComposedChart>
          </ResponsiveContainer>
        </ClientOnly>
      )}

      {!loading && !error && rows.length === 0 && (
        <div className="h-[280px] flex items-center justify-center text-muted-foreground text-sm">
          No data available for this time range
        </div>
      )}

      {/* Source label */}
      <div className="mt-2 text-[10px] text-muted-foreground text-right">
        Source: Finnhub &middot; {resolution} resolution
      </div>
    </section>
  );
}
