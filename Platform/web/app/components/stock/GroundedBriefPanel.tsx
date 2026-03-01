"use client";

import { useState, useEffect } from "react";
import { Loader2, AlertCircle, RefreshCw, Database, ShieldCheck, ShieldAlert } from "lucide-react";
import { authGet } from "@/lib/fetchWithAuth";
import { COMPLIANCE } from "../../lib/compliance";

type FactPack = {
  symbol: string;
  as_of_utc: string;
  price: number | null;
  day_change_pct: number | null;
  market_cap: number | null;
  pe_ttm: number | null;
  peg: number | null;
  revenue_yoy: number | null;
  eps_yoy: number | null;
  fcf_yoy: number | null;
  gross_margin: number | null;
  op_margin: number | null;
  fcf_margin: number | null;
  roe: number | null;
  debt_to_equity: number | null;
  beta: number | null;
  volatility_30d: number | null;
  max_drawdown_1y: number | null;
  sector: string | null;
  company_name: string | null;
  forward_estimates_available: boolean;
  sources: Record<string, { as_of_utc: string; endpoints: string[] }>;
};

type GroundedBriefResponse = {
  symbol: string;
  as_of_utc: string;
  brief_markdown: string;
  citations: string[];
  fact_pack: FactPack;
  validation_passed: boolean;
  validation_errors: string[];
};

function formatNum(v: number | null, opts?: { suffix?: string; prefix?: string; decimals?: number }): string {
  if (v === null || v === undefined) return "—";
  const d = opts?.decimals ?? 2;
  const formatted = v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  return `${opts?.prefix ?? ""}${formatted}${opts?.suffix ?? ""}`;
}

function formatMarketCap(v: number | null): string {
  if (v === null || v === undefined) return "—";
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
  return `$${v.toLocaleString()}`;
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1 border-b border-border/30 last:border-0">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span className="text-[11px] font-mono font-medium">{value}</span>
    </div>
  );
}

export function GroundedBriefPanel({ ticker }: { ticker: string }) {
  const [data, setData] = useState<GroundedBriefResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    const res = await authGet<GroundedBriefResponse>(
      `/api/stocks/${encodeURIComponent(ticker)}/brief`,
    );
    if (res.ok) {
      setData(res.data);
    } else {
      setError(res.error || "Failed to load brief");
    }
    setLoading(false);
  }

  useEffect(() => {
    if (ticker) load();
  }, [ticker]);

  if (loading && !data) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">FINNHUB-GROUNDED BRIEF</div>
        <div className="mt-4 flex items-center justify-center gap-2 py-8 text-muted-foreground text-sm">
          <Loader2 size={14} className="animate-spin" />
          Loading Finnhub data & generating brief...
        </div>
      </section>
    );
  }

  if (error && !data) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">FINNHUB-GROUNDED BRIEF</div>
        <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
          <AlertCircle size={14} />
          {error}
        </div>
        <button
          type="button"
          onClick={load}
          className="mt-2 text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <RefreshCw size={12} /> Retry
        </button>
      </section>
    );
  }

  if (!data) return null;

  const fp = data.fact_pack;
  const providers = Object.keys(fp.sources || {});

  return (
    <section className="bt-panel p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database size={14} className="text-muted-foreground" />
          <span className="bt-panel-title">FINNHUB-GROUNDED BRIEF</span>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="text-muted-foreground hover:text-foreground transition-colors"
          title="Refresh brief"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Validation badge + data source */}
      <div className="flex items-center gap-2 flex-wrap">
        {data.validation_passed ? (
          <div className="flex items-center gap-1 text-[10px] text-risk-on bg-risk-on/10 rounded px-2 py-0.5">
            <ShieldCheck size={10} />
            <span>Validated against Finnhub</span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-[10px] text-orange-400 bg-orange-400/10 rounded px-2 py-0.5">
            <ShieldAlert size={10} />
            <span>Deterministic fallback (no AI)</span>
          </div>
        )}
        <div className="flex items-center gap-1 text-[10px] text-muted-foreground bg-panel rounded px-2 py-0.5">
          <Database size={10} />
          <span>Source: {providers.join(", ") || "finnhub"}</span>
        </div>
        <div className="text-[10px] text-muted-foreground">
          as of {new Date(data.as_of_utc).toLocaleString()}
        </div>
      </div>

      {/* Key metrics grid */}
      <div>
        <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
          Snapshot (Finnhub)
        </div>
        <div className="grid gap-x-6 gap-y-0 sm:grid-cols-2">
          <MetricRow label="Price" value={formatNum(fp.price, { prefix: "$" })} />
          <MetricRow
            label="Day Change"
            value={
              fp.day_change_pct !== null
                ? `${fp.day_change_pct >= 0 ? "+" : ""}${fp.day_change_pct.toFixed(2)}%`
                : "—"
            }
          />
          <MetricRow label="Market Cap" value={formatMarketCap(fp.market_cap)} />
          <MetricRow label="P/E (TTM)" value={formatNum(fp.pe_ttm)} />
          <MetricRow label="PEG" value={formatNum(fp.peg)} />
          <MetricRow label="Beta" value={formatNum(fp.beta)} />
        </div>
      </div>

      {/* Margins & growth */}
      {(fp.gross_margin !== null || fp.op_margin !== null || fp.roe !== null || fp.revenue_yoy !== null) && (
        <div>
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
            Fundamentals
          </div>
          <div className="grid gap-x-6 gap-y-0 sm:grid-cols-2">
            <MetricRow label="Gross Margin" value={formatNum(fp.gross_margin, { suffix: "%" })} />
            <MetricRow label="Op. Margin" value={formatNum(fp.op_margin, { suffix: "%" })} />
            <MetricRow label="FCF Margin" value={formatNum(fp.fcf_margin, { suffix: "%" })} />
            <MetricRow label="ROE" value={formatNum(fp.roe, { suffix: "%" })} />
            <MetricRow label="Debt/Equity" value={formatNum(fp.debt_to_equity)} />
            <MetricRow label="Revenue YoY" value={formatNum(fp.revenue_yoy, { suffix: "%" })} />
            <MetricRow label="EPS YoY" value={formatNum(fp.eps_yoy, { suffix: "%" })} />
            <MetricRow label="FCF YoY" value={formatNum(fp.fcf_yoy, { suffix: "%" })} />
          </div>
        </div>
      )}

      {/* AI Brief (markdown rendered as plain text) */}
      <div>
        <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
          {data.validation_passed ? "AI Analysis" : "Data Summary"}
        </div>
        <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-line">
          {data.brief_markdown
            .replace(/^#{1,3}\s+/gm, "")
            .replace(/\*\*(.*?)\*\*/g, "$1")
            .replace(/\*(.*?)\*/g, "$1")
            .trim()}
        </div>
      </div>

      {/* Citations */}
      {data.citations?.length > 0 && (
        <div className="pt-1 border-t border-border/50">
          <span className="text-[10px] text-muted-foreground">
            Sources: {data.citations.join(", ")}
          </span>
        </div>
      )}

      {/* Disclaimer */}
      <div className="pt-1 border-t border-border/50">
        <p className="text-[10px] text-muted-foreground/60">
          {COMPLIANCE.NOT_INVESTMENT_ADVICE}
        </p>
      </div>
    </section>
  );
}
