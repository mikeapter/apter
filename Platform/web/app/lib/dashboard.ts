export type MarketRegime = "RISK-ON" | "NEUTRAL" | "RISK-OFF";
export type SignalType = "BUY" | "SELL" | "HOLD";
export type ConfidenceLevel = "Low" | "Medium" | "High";
export type UserTier = "FREE" | "STANDARD" | "PRO";

export type SignalRow = {
  ticker: string;
  signal: SignalType;
  timestamp: string; // keep as display-ready string for now
  confidence: ConfidenceLevel;
};

export type DiagnosticCard = {
  label: string;
  state: string;
  summary: string;
  tone?: "on" | "neutral" | "off";
};

export type RegimeTransition = {
  timestamp: string;
  from: MarketRegime;
  to: MarketRegime;
  note: string;
};

export type NoTradePeriod = {
  start: string;
  end: string;
  reason: string;
};

export type SignalFrequency = {
  window: string;
  count: number;
  comment: string;
};

export type SystemHistory = {
  transitions: RegimeTransition[];
  noTradePeriods: NoTradePeriod[];
  signalFrequency: SignalFrequency[];
};

export type DashboardData = {
  regime: MarketRegime;
  tier: UserTier;
  systemAssessment: string[];
  signals: SignalRow[];
  diagnostics: DiagnosticCard[];
  history: SystemHistory;
  guidance: string;
};

/**
 * Institutional placeholder data (safe tone, no promotional performance language, no prediction).
 */
export const sampleDashboardData: DashboardData = {
  regime: "NEUTRAL",
  tier: "PRO",
  systemAssessment: [
    "Market conditions currently support selective exposure only.",
    "Volatility remains elevated; trend strength is inconsistent.",
    "Risk posture should prioritize capital preservation under current conditions.",
  ],
  signals: [
    { ticker: "AAPL", signal: "HOLD", timestamp: "2026-02-02 13:12:08", confidence: "Medium" },
    { ticker: "MSFT", signal: "HOLD", timestamp: "2026-02-02 13:11:42", confidence: "High" },
    { ticker: "NVDA", signal: "SELL", timestamp: "2026-02-02 13:10:19", confidence: "Low" },
    { ticker: "SPY",  signal: "HOLD", timestamp: "2026-02-02 13:09:05", confidence: "Medium" },
    { ticker: "TLT",  signal: "BUY",  timestamp: "2026-02-02 13:07:33", confidence: "Low" },
  ],
  diagnostics: [
    {
      label: "Volatility Regime",
      state: "Elevated",
      summary: "Realized volatility is above trailing median; risk budget should remain constrained.",
      tone: "off",
    },
    {
      label: "Correlation Regime",
      state: "Moderate",
      summary: "Cross-asset correlation is stable; diversification benefit is present but reduced.",
      tone: "neutral",
    },
    {
      label: "Trend Strength",
      state: "Weak",
      summary: "Directional persistence is inconsistent; signals require higher confirmation threshold.",
      tone: "off",
    },
    {
      label: "Liquidity Conditions",
      state: "Normal",
      summary: "Spreads and depth are within typical range for monitored instruments.",
      tone: "on",
    },
  ],
  history: {
    transitions: [
      {
        timestamp: "2026-02-01 15:10:00",
        from: "NEUTRAL",
        to: "RISK-OFF",
        note: "Cross-asset correlation increased and volatility expanded.",
      },
      {
        timestamp: "2026-02-02 10:05:00",
        from: "RISK-OFF",
        to: "NEUTRAL",
        note: "Correlation normalized; volatility stabilized relative to prior session.",
      },
    ],
    noTradePeriods: [
      {
        start: "2026-01-31 09:30:00",
        end: "2026-01-31 11:15:00",
        reason: "Event risk elevated; spreads widened beyond internal tolerance.",
      },
      {
        start: "2026-02-01 14:00:00",
        end: "2026-02-01 15:00:00",
        reason: "Regime transition underway; signal quality below threshold.",
      },
    ],
    signalFrequency: [
      {
        window: "Last 24h",
        count: 14,
        comment: "Below normal due to elevated uncertainty.",
      },
      {
        window: "Last 7d",
        count: 83,
        comment: "Within range; higher dispersion across instruments.",
      },
      {
        window: "Last 30d",
        count: 352,
        comment: "Reduced cadence during multiple no-trade intervals.",
      },
    ],
  },
  guidance: "No action is often the correct action.",
};

/**
 * If/when your API returns dashboard data, normalize it here.
 * This is intentionally conservative: if shape is unknown, we fall back to sample.
 */
export function normalizeDashboardData(payload: any): DashboardData | null {
  const raw = payload?.data ?? payload;
  if (!raw || typeof raw !== "object") return null;

  const regime = raw.regime;
  const isRegime = (v: any): v is MarketRegime =>
    v === "RISK-ON" || v === "NEUTRAL" || v === "RISK-OFF";

  if (!isRegime(regime)) return null;

  const tier: UserTier =
    raw.tier === "FREE" || raw.tier === "STANDARD" || raw.tier === "PRO"
      ? raw.tier
      : sampleDashboardData.tier;

  const systemAssessment: string[] = Array.isArray(raw.systemAssessment)
    ? raw.systemAssessment.filter((x: any) => typeof x === "string").slice(0, 6)
    : sampleDashboardData.systemAssessment;

  const signals: SignalRow[] = Array.isArray(raw.signals)
    ? raw.signals
        .filter((r: any) => r && typeof r === "object")
        .map((r: any) => ({
          ticker: String(r.ticker ?? "").toUpperCase().trim(),
          signal: (String(r.signal ?? "HOLD").toUpperCase() as SignalType) || "HOLD",
          timestamp: String(r.timestamp ?? ""),
          confidence: (String(r.confidence ?? "Medium") as ConfidenceLevel) || "Medium",
        }))
        .filter((r: SignalRow) => !!r.ticker && !!r.timestamp)
        .slice(0, 50)
    : sampleDashboardData.signals;

  const diagnostics: DiagnosticCard[] = Array.isArray(raw.diagnostics)
    ? raw.diagnostics
        .filter((d: any) => d && typeof d === "object")
        .map((d: any) => ({
          label: String(d.label ?? ""),
          state: String(d.state ?? ""),
          summary: String(d.summary ?? ""),
          tone:
            d.tone === "on" || d.tone === "neutral" || d.tone === "off"
              ? d.tone
              : undefined,
        }))
        .filter((d: DiagnosticCard) => !!d.label && !!d.state && !!d.summary)
        .slice(0, 12)
    : sampleDashboardData.diagnostics;

  const history = raw.history && typeof raw.history === "object" ? raw.history : null;

  const normalized: DashboardData = {
    regime,
    tier,
    systemAssessment,
    signals,
    diagnostics,
    history: {
      transitions: Array.isArray(history?.transitions) ? history.transitions : sampleDashboardData.history.transitions,
      noTradePeriods: Array.isArray(history?.noTradePeriods) ? history.noTradePeriods : sampleDashboardData.history.noTradePeriods,
      signalFrequency: Array.isArray(history?.signalFrequency) ? history.signalFrequency : sampleDashboardData.history.signalFrequency,
    },
    guidance: typeof raw.guidance === "string" ? raw.guidance : sampleDashboardData.guidance,
  };

  return normalized;
}
