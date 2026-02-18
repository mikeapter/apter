export type MarketRegime = "RISK-ON" | "NEUTRAL" | "RISK-OFF";
export type SignalType = "BULLISH_BIAS" | "NEUTRAL_BIAS" | "BEARISH_BIAS";
export type ConfidenceLevel = "Low" | "Medium" | "High";
export type UserTier = "free" | "standard" | "pro";
export type TimeRange = "1D" | "1W" | "1M" | "3M" | "1Y" | "ALL";

export type SignalRow = {
  ticker: string;
  signal: SignalType;
  timestamp: string;
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

export type PortfolioHolding = {
  id: string;
  ticker: string;
  shares: number;
  purchasePrice: number;
  addedAt: string;
};

export type MarketMover = {
  ticker: string;
  companyName: string;
  price: number;
  change: number;
  changePct: number;
  volume: string;
  grade: number;
};

export type PerformanceDataPoint = {
  date: string;
  portfolio: number;
  sp500: number;
  nasdaq: number;
  dow: number;
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
  tier: "free",
  systemAssessment: [
    "Market conditions currently support selective exposure only.",
    "Volatility remains elevated; trend strength is inconsistent.",
    "Risk posture should prioritize capital preservation under current conditions.",
  ],
  signals: [
    { ticker: "AAPL", signal: "NEUTRAL_BIAS", timestamp: "2026-02-02 13:12:08", confidence: "Medium" },
    { ticker: "MSFT", signal: "NEUTRAL_BIAS", timestamp: "2026-02-02 13:11:42", confidence: "High" },
    { ticker: "NVDA", signal: "BEARISH_BIAS", timestamp: "2026-02-02 13:10:19", confidence: "Low" },
    { ticker: "SPY",  signal: "NEUTRAL_BIAS", timestamp: "2026-02-02 13:09:05", confidence: "Medium" },
    { ticker: "TLT",  signal: "BULLISH_BIAS", timestamp: "2026-02-02 13:07:33", confidence: "Low" },
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
      { window: "Last 24h", count: 14, comment: "Below normal due to elevated uncertainty." },
      { window: "Last 7d", count: 83, comment: "Within range; higher dispersion across instruments." },
      { window: "Last 30d", count: 352, comment: "Reduced cadence during multiple no-trade intervals." },
    ],
  },
  guidance: "No action is often the correct action.",
};

/** Sample market movers for the dashboard. */
export const sampleGainers: MarketMover[] = [
  { ticker: "SMCI", companyName: "Super Micro Computer", price: 892.45, change: 67.12, changePct: 8.13, volume: "12.4M", grade: 8 },
  { ticker: "PLTR", companyName: "Palantir Technologies", price: 78.23, change: 4.56, changePct: 6.19, volume: "45.2M", grade: 7 },
  { ticker: "ARM", companyName: "Arm Holdings", price: 164.89, change: 8.32, changePct: 5.31, volume: "8.7M", grade: 7 },
  { ticker: "CRWD", companyName: "CrowdStrike", price: 342.10, change: 14.78, changePct: 4.51, volume: "5.1M", grade: 6 },
  { ticker: "COIN", companyName: "Coinbase Global", price: 267.34, change: 10.45, changePct: 4.07, volume: "9.3M", grade: 5 },
];

export const sampleLosers: MarketMover[] = [
  { ticker: "MRNA", companyName: "Moderna", price: 38.42, change: -3.87, changePct: -9.15, volume: "18.6M", grade: 3 },
  { ticker: "ENPH", companyName: "Enphase Energy", price: 68.91, change: -4.23, changePct: -5.78, volume: "7.2M", grade: 2 },
  { ticker: "PYPL", companyName: "PayPal Holdings", price: 62.15, change: -2.89, changePct: -4.44, volume: "14.8M", grade: 4 },
  { ticker: "BA", companyName: "Boeing", price: 178.30, change: -6.45, changePct: -3.49, volume: "11.1M", grade: 3 },
  { ticker: "INTC", companyName: "Intel", price: 21.56, change: -0.67, changePct: -3.01, volume: "42.5M", grade: 2 },
];

/** Sample performance data for charts. */
export function generatePerformanceData(range: TimeRange): PerformanceDataPoint[] {
  const points: PerformanceDataPoint[] = [];
  let numPoints: number;
  switch (range) {
    case "1D": numPoints = 78; break;
    case "1W": numPoints = 5; break;
    case "1M": numPoints = 22; break;
    case "3M": numPoints = 65; break;
    case "1Y": numPoints = 252; break;
    case "ALL": numPoints = 504; break;
    default: numPoints = 22;
  }

  const baseDate = new Date("2026-02-16");
  let pVal = 100000;
  let sp = 100;
  let nq = 100;
  let dj = 100;

  for (let i = numPoints; i >= 0; i--) {
    const d = new Date(baseDate);
    if (range === "1D") {
      d.setMinutes(d.getMinutes() - i * 5);
    } else {
      d.setDate(d.getDate() - i);
    }

    pVal += pVal * (Math.random() * 0.02 - 0.008);
    sp += sp * (Math.random() * 0.015 - 0.006);
    nq += nq * (Math.random() * 0.018 - 0.007);
    dj += dj * (Math.random() * 0.012 - 0.005);

    points.push({
      date: range === "1D"
        ? d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
        : d.toISOString().slice(0, 10),
      portfolio: Math.round(pVal),
      sp500: parseFloat(sp.toFixed(2)),
      nasdaq: parseFloat(nq.toFixed(2)),
      dow: parseFloat(dj.toFixed(2)),
    });
  }

  return points;
}

/**
 * If/when your API returns dashboard data, normalize it here.
 */
export function normalizeDashboardData(payload: any): DashboardData | null {
  const raw = payload?.data ?? payload;
  if (!raw || typeof raw !== "object") return null;

  const regime = raw.regime;
  const isRegime = (v: any): v is MarketRegime =>
    v === "RISK-ON" || v === "NEUTRAL" || v === "RISK-OFF";

  if (!isRegime(regime)) return null;

  const tier: UserTier =
    raw.tier === "free" || raw.tier === "standard" || raw.tier === "pro"
      ? raw.tier
      : sampleDashboardData.tier;

  const systemAssessment: string[] = Array.isArray(raw.systemAssessment)
    ? raw.systemAssessment.filter((x: any) => typeof x === "string").slice(0, 6)
    : sampleDashboardData.systemAssessment;

  const toSignalType = (value: any): SignalType => {
    const normalized = String(value ?? "").toUpperCase().trim();

    if (normalized === "BULLISH_BIAS") return "BULLISH_BIAS";
    if (normalized === "NEUTRAL_BIAS") return "NEUTRAL_BIAS";
    if (normalized === "BEARISH_BIAS") return "BEARISH_BIAS";

    if (normalized === "BUY") return "BULLISH_BIAS";
    if (normalized === "HOLD") return "NEUTRAL_BIAS";
    if (normalized === "SELL") return "BEARISH_BIAS";

    return "NEUTRAL_BIAS";
  };

  const signals: SignalRow[] = Array.isArray(raw.signals)
    ? raw.signals
        .filter((r: any) => r && typeof r === "object")
        .map((r: any) => ({
          ticker: String(r.ticker ?? "").toUpperCase().trim(),
          signal: toSignalType(r.signal),
          timestamp: String(r.timestamp ?? r.ts ?? ""),
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
          summary: String(d.summary ?? d.note ?? ""),
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
      transitions: Array.isArray(history?.transitions)
        ? history.transitions
        : sampleDashboardData.history.transitions,
      noTradePeriods: Array.isArray(history?.noTradePeriods)
        ? history.noTradePeriods
        : sampleDashboardData.history.noTradePeriods,
      signalFrequency: Array.isArray(history?.signalFrequency)
        ? history.signalFrequency
        : sampleDashboardData.history.signalFrequency,
    },
    guidance: typeof raw.guidance === "string" ? raw.guidance : sampleDashboardData.guidance,
  };

  return normalized;
}
