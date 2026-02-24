import { COMPLIANCE } from "../../lib/compliance";

const PILLARS = [
  {
    name: "Quality",
    weight: "25%",
    description:
      "Measures the durability and efficiency of the business. Higher-quality companies tend to sustain returns through cycles.",
    metrics: [
      "Return on Equity (ROE)",
      "Return on Invested Capital (ROIC)",
      "Gross Margin",
      "Operating Margin",
      "Free Cash Flow Margin",
      "Asset Turnover",
    ],
  },
  {
    name: "Value",
    weight: "20%",
    description:
      "Assesses whether the current price offers a reasonable entry relative to earnings, cash flow, and book value.",
    metrics: [
      "Price / Earnings (P/E)",
      "Price / Book (P/B)",
      "Price / Sales (P/S)",
      "EV / EBITDA",
      "Free Cash Flow Yield",
    ],
  },
  {
    name: "Growth",
    weight: "20%",
    description:
      "Captures the trajectory of revenue, earnings, and free cash flow over recent and multi-year periods.",
    metrics: [
      "Revenue Growth (YoY)",
      "Earnings Growth (YoY)",
      "FCF Growth (YoY)",
      "Revenue 3-Year CAGR",
      "Earnings 3-Year CAGR",
    ],
  },
  {
    name: "Momentum",
    weight: "20%",
    description:
      "Evaluates price trend strength and positioning relative to key moving averages.",
    metrics: [
      "Price vs. 50-Day SMA",
      "Price vs. 200-Day SMA",
      "RSI (14-day)",
      "1-Month Return",
      "3-Month Return",
      "6-Month Return",
    ],
  },
  {
    name: "Risk",
    weight: "15%",
    description:
      "Penalizes stocks with excessive leverage, volatility, drawdown, or insufficient liquidity buffers.",
    metrics: [
      "30-Day Volatility",
      "Max Drawdown (1-Year)",
      "Debt / Equity",
      "Interest Coverage",
      "Current Ratio",
      "Beta",
    ],
  },
] as const;

const BANDS = [
  { range: "8.0 \u2013 10.0", label: "Strong Setup", color: "text-risk-on", border: "border-risk-on/30" },
  { range: "6.0 \u2013 7.9", label: "Constructive", color: "text-risk-neutral", border: "border-risk-neutral/30" },
  { range: "4.0 \u2013 5.9", label: "Neutral", color: "text-muted-foreground", border: "border-border" },
  { range: "0.0 \u2013 3.9", label: "Weak Setup", color: "text-risk-off", border: "border-risk-off/30" },
] as const;

export const metadata = {
  title: "Methodology \u2014 Apter Conviction Score",
  description:
    "How the Apter Conviction Score works: pillars, score interpretation, and data sources.",
};

export default function MethodologyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 sm:px-6 py-16 space-y-12">
      {/* Title */}
      <header className="space-y-3">
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
          How the Conviction Score Works
        </h1>
        <p className="text-sm text-muted-foreground leading-relaxed max-w-xl">
          The Apter Conviction Score is a composite 0&ndash;10 rating that
          synthesizes fundamental quality, valuation, growth trajectory, price
          momentum, and risk characteristics into a single defensible number.
        </p>
      </header>

      {/* Five Pillars */}
      <section className="space-y-6">
        <h2 className="text-lg font-semibold">The Five Pillars</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Each stock is evaluated across five equally-structured pillars. Within
          each pillar, individual metrics are weighted and normalized against
          sector peers before being combined into a pillar score (0&ndash;10).
          Pillar scores are then blended using the weights shown below.
        </p>

        <div className="space-y-4">
          {PILLARS.map((p) => (
            <div
              key={p.name}
              className="rounded-md border border-border bg-card p-4 space-y-2"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">{p.name}</h3>
                <span className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">
                  Weight: {p.weight}
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {p.description}
              </p>
              <ul className="grid grid-cols-2 gap-x-4 gap-y-1 pt-1">
                {p.metrics.map((m) => (
                  <li
                    key={m}
                    className="text-[11px] text-muted-foreground before:content-['\2022'] before:mr-1.5 before:text-border"
                  >
                    {m}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* Risk Gates */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Risk Gates &amp; Adjustments</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          After the composite score is calculated, the system applies hard caps
          and penalties for extreme risk conditions. These include excessive
          leverage, persistent negative free cash flow with high dilution, and
          extreme volatility or drawdown. Risk gates ensure that a stock cannot
          receive a high conviction score while exhibiting dangerous financial
          characteristics.
        </p>
      </section>

      {/* Score bands */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Score Interpretation</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          The overall score maps to one of four plain-language bands:
        </p>
        <div className="grid gap-2">
          {BANDS.map((b) => (
            <div
              key={b.range}
              className={`flex items-center gap-4 rounded-md border ${b.border} bg-card px-4 py-2.5`}
            >
              <span className="font-mono text-sm font-semibold w-24">
                {b.range}
              </span>
              <span className={`text-sm font-medium ${b.color}`}>
                {b.label}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Confidence */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Confidence Score</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Each conviction score is accompanied by a confidence percentage that
          reflects data completeness. Missing metrics, unavailable peer-group
          comparisons, and stale data reduce confidence. A score with low
          confidence should be interpreted with additional caution.
        </p>
      </section>

      {/* Update frequency */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Update Frequency</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Scores are updated regularly; frequency varies by data availability
          and market conditions. Fundamental data refreshes on quarterly
          reporting cycles, while momentum and risk metrics update more
          frequently as price data changes.
        </p>
      </section>

      {/* Time horizon */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Time Horizon</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          The Conviction Score is designed for swing and position-level
          decision-making, not intraday trading. The fundamental pillars
          (Quality, Value, Growth) reflect medium-term characteristics, while
          Momentum captures weeks-to-months trend behavior.
        </p>
      </section>

      {/* Data sources */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Data Sources</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          The model draws from publicly available financial data including SEC
          filings, market price feeds, and derived analytics. All metrics are
          computed from objective, verifiable data points.
        </p>
      </section>

      {/* What it is / isn't */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">
          What It Is &amp; What It Isn&apos;t
        </h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="rounded-md border border-risk-on/20 bg-risk-on/5 p-4 space-y-2">
            <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-risk-on">
              What it is
            </div>
            <ul className="space-y-1.5 text-xs text-muted-foreground">
              <li>A structured, quantitative framework for evaluating stocks</li>
              <li>An aggregation of publicly available fundamental and technical data</li>
              <li>A starting point for your own research and decision-making</li>
              <li>Transparent in its inputs and methodology</li>
            </ul>
          </div>
          <div className="rounded-md border border-risk-off/20 bg-risk-off/5 p-4 space-y-2">
            <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-risk-off">
              What it is not
            </div>
            <ul className="space-y-1.5 text-xs text-muted-foreground">
              <li>Not a buy, sell, or hold recommendation</li>
              <li>Not personalized investment advice</li>
              <li>Not a guarantee of future performance</li>
              <li>Not a substitute for professional financial counsel</li>
            </ul>
          </div>
        </div>
      </section>

      {/* Disclaimer */}
      <footer className="border-t border-border pt-6">
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          {COMPLIANCE.NOT_INVESTMENT_ADVICE} {COMPLIANCE.DISCLOSURE_BANNER}
        </p>
      </footer>
    </div>
  );
}
