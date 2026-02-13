import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function nowIso() {
  return new Date().toISOString();
}

export async function GET() {
  return NextResponse.json({
    mode: "analysis_only",
    tier: "PRO",
    regime: "NEUTRAL",
    market_regime: "NEUTRAL",
    timestamp: nowIso(),
    freshness_seconds: 10,
    data_live: true,
    systemAssessment: [
      "Market conditions currently support selective exposure only.",
      "Volatility remains elevated; trend strength is inconsistent.",
      "Risk posture should prioritize capital preservation under current conditions.",
    ],
    system_assessment: [
      "Market conditions currently support selective exposure only.",
      "Volatility remains elevated; trend strength is inconsistent.",
      "Risk posture should prioritize capital preservation under current conditions.",
    ],
    signals: [
      { ticker: "AAPL", signal: "NEUTRAL_BIAS", ts: nowIso(), confidence: "Medium" },
      { ticker: "MSFT", signal: "NEUTRAL_BIAS", ts: nowIso(), confidence: "High" },
      { ticker: "NVDA", signal: "BEARISH_BIAS", ts: nowIso(), confidence: "Low" },
      { ticker: "SPY", signal: "NEUTRAL_BIAS", ts: nowIso(), confidence: "Medium" },
      { ticker: "TLT", signal: "BULLISH_BIAS", ts: nowIso(), confidence: "Low" },
    ],
    signal_matrix: [
      { ticker: "AAPL", signal: "NEUTRAL_BIAS", ts: nowIso(), confidence: "Medium" },
      { ticker: "MSFT", signal: "NEUTRAL_BIAS", ts: nowIso(), confidence: "High" },
      { ticker: "NVDA", signal: "BEARISH_BIAS", ts: nowIso(), confidence: "Low" },
      { ticker: "SPY", signal: "NEUTRAL_BIAS", ts: nowIso(), confidence: "Medium" },
      { ticker: "TLT", signal: "BULLISH_BIAS", ts: nowIso(), confidence: "Low" },
    ],
    diagnostics: [
      {
        label: "Volatility Regime",
        state: "Elevated",
        note: "Realized volatility is above trailing median; risk budget should remain constrained.",
      },
      {
        label: "Correlation Regime",
        state: "Moderate",
        note: "Cross-asset correlation is stable; diversification benefit is present but reduced.",
      },
      {
        label: "Trend Strength",
        state: "Weak",
        note: "Directional persistence is inconsistent; signals require higher confirmation threshold.",
      },
      {
        label: "Liquidity Conditions",
        state: "Normal",
        note: "Primary venues exhibit stable spreads; slippage risk is contained.",
      },
    ],
    system_history: {
      regime_transitions: [
        { ts: "2026-02-01 15:10:00", from: "NEUTRAL", to: "RISK-OFF", note: "Volatility expanded; correlation increased." },
        { ts: "2026-02-02 10:05:00", from: "RISK-OFF", to: "NEUTRAL", note: "Correlation normalized; volatility stabilized." },
      ],
      no_trade_periods: [
        { start: "2026-01-31 09:30:00", end: "2026-01-31 11:15:00", reason: "Event risk elevated; spreads widened beyond tolerance." },
        { start: "2026-02-01 14:00:00", end: "2026-02-01 15:00:00", reason: "Regime transition underway; signal quality below threshold." },
      ],
      signal_frequency: [
        { window: "Last 24h", count: 14, comment: "Below normal due to elevated uncertainty." },
        { window: "Last 7d", count: 83, comment: "Within range; higher dispersion across instruments." },
        { window: "Last 30d", count: 352, comment: "Reduced cadence during multiple no-trade intervals." },
      ],
      footer_note: "Process integrity is prioritized over promotional performance presentation.",
    },
    guidance: "No action is often the correct action.",
    footer_guidance: "No action is often the correct action.",
    disclosure: {
      text: "Information is for educational and research purposes only. Not investment advice. Apter Financial is not acting as a registered investment adviser.",
    },
  });
}
