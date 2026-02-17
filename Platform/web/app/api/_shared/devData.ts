import { randomUUID } from "crypto";

export type PlanTier = "free" | "standard" | "pro";

export type Plan = {
  tier: PlanTier;
  name: string;
  price_usd_month: number;
  target_user: string;
  features: string[];
  exclusions: string[];
  limits: {
    signal_delay_seconds: number;
    max_signals_per_response: number;
    history_days: number;
    alerts: boolean;
  };
};

export type PlansResponse = {
  plans: Plan[];
  as_of: string;
};

export type RegisterResponse = {
  user_id: number;
  email: string;
  access_token: string;
  token_type: string;
};

export type LoginResponse =
  | { requires_2fa: true; user_id: number; message: string }
  | { access_token: string; token_type: string };

export type SubscriptionMeResponse = {
  tier: PlanTier;
  plan: Plan;
  status: string;
  updated_at: string;
};

export type SignalsFeedResponse = {
  tier: PlanTier;
  mode: string;
  signal_delay_seconds: number;
  signals: Array<{
    id?: string;
    ts?: number;
    status?: string;
    execution_mode?: string;
    symbol?: string;
    side?: string;
    qty?: number;
    strategy_id?: string;
    confidence?: number;
    rationale?: string;
    blocked?: boolean;
    reasons?: string[];
  }>;
  generated_at: string;
};

type UserRecord = {
  user_id: number;
  email: string;
  password: string;
};

type SessionRecord = {
  token: string;
  user_id: number;
  email: string;
  tier: PlanTier;
  status: string;
  updated_at: string;
};

let nextUserId = 1;
const usersByEmail = new Map<string, UserRecord>();
const sessionsByToken = new Map<string, SessionRecord>();

export function nowIso() {
  return new Date().toISOString();
}

export function isPlanTier(v: any): v is PlanTier {
  return v === "free" || v === "standard" || v === "pro";
}

const PLANS: Plan[] = [
  {
    tier: "free",
    name: "Free",
    price_usd_month: 0,
    target_user: "Self-directed investors who want institutional-quality analytics at no cost.",
    features: [
      "Full financial statements",
      "Institutional dashboard UI",
      "Basic screener (limited filters)",
      "Watchlist with cost basis tracking",
      "Earnings calendar",
      "Basic factor score",
      "AI summary (short, factual)",
    ],
    exclusions: [
      "Advanced screener filters",
      "Risk score engine",
      "Portfolio risk analysis",
      "Insider activity tracking",
      "Historical signal backtests",
    ],
    limits: {
      signal_delay_seconds: 86400,
      max_signals_per_response: 0,
      history_days: 7,
      alerts: false,
    },
  },
  {
    tier: "standard",
    name: "Standard",
    price_usd_month: 25,
    target_user: "Serious retail investors who need advanced research and risk analytics.",
    features: [
      "Everything in Free",
      "Advanced screener",
      "Risk score engine (security + portfolio level)",
      "Portfolio risk analysis (concentration, volatility, drawdown, correlation)",
      "Insider activity tracking",
      "Earnings probability model (scenario probabilities)",
      "News impact scoring",
      "Historical signal backtests (with hypothetical-performance disclaimer)",
    ],
    exclusions: [
      "Regime detection engine",
      "Factor exposure analysis",
      "Beta-adjusted risk modeling",
      "AI 10-K deep summary",
      "Sector rotation dashboard",
    ],
    limits: {
      signal_delay_seconds: 300,
      max_signals_per_response: 25,
      history_days: 90,
      alerts: false,
    },
  },
  {
    tier: "pro",
    name: "Pro",
    price_usd_month: 49,
    target_user: "Advanced users who want institutional-style hedge-fund analytics (analytics only).",
    features: [
      "Everything in Standard",
      "Regime detection engine",
      "Factor exposure analysis",
      "Beta-adjusted risk modeling",
      "Event volatility forecasts",
      "AI 10-K deep summary",
      "Sector rotation dashboard",
      "Allocation scenario explorer (comparative what-if scenarios)",
    ],
    exclusions: ["None — full platform access"],
    limits: {
      signal_delay_seconds: 0,
      max_signals_per_response: 50,
      history_days: 365,
      alerts: false,
    },
  },
];

export function getPlans(): Plan[] {
  return PLANS;
}

export function getPlan(tier: PlanTier): Plan {
  const p = PLANS.find((x) => x.tier === tier);
  return p ?? PLANS[0];
}

function issueToken() {
  return `dev_${randomUUID().replace(/-/g, "")}`;
}

export function getBearerToken(req: Request): string | null {
  const raw = req.headers.get("authorization") || "";
  const m = raw.match(/^Bearer\s+(.+)$/i);
  return m?.[1]?.trim() || null;
}

export function resolveTierFromRequest(req: Request): PlanTier {
  const token = getBearerToken(req);
  if (!token) return "free";
  const sess = sessionsByToken.get(token);
  return sess?.tier ?? "free";
}

export function getSessionFromRequest(req: Request): SessionRecord | null {
  const token = getBearerToken(req);
  if (!token) return null;
  return sessionsByToken.get(token) ?? null;
}

export function registerUser(email: string, password: string): RegisterResponse {
  const e = (email || "").trim().toLowerCase();
  const p = (password || "").trim();

  if (!e || !e.includes("@")) {
    throw new Error("Invalid email.");
  }
  if (!p || p.length < 4) {
    throw new Error("Password must be at least 4 characters (dev policy).");
  }

  let u = usersByEmail.get(e);
  if (!u) {
    u = { user_id: nextUserId++, email: e, password: p };
    usersByEmail.set(e, u);
  }

  const token = issueToken();
  const sess: SessionRecord = {
    token,
    user_id: u.user_id,
    email: u.email,
    tier: "free",
    status: "active",
    updated_at: nowIso(),
  };
  sessionsByToken.set(token, sess);

  return { user_id: u.user_id, email: u.email, access_token: token, token_type: "bearer" };
}

export function loginUser(email: string, password: string): LoginResponse {
  const e = (email || "").trim().toLowerCase();
  const p = (password || "").trim();

  const u = usersByEmail.get(e);
  if (!u) {
    throw new Error("Unknown email. Register first (dev).");
  }
  if (u.password !== p) {
    throw new Error("Invalid credentials.");
  }

  const token = issueToken();
  const sess: SessionRecord = {
    token,
    user_id: u.user_id,
    email: u.email,
    tier: "free",
    status: "active",
    updated_at: nowIso(),
  };
  sessionsByToken.set(token, sess);

  return { access_token: token, token_type: "bearer" };
}

export function setTierForToken(token: string, tier: PlanTier) {
  const sess = sessionsByToken.get(token);
  if (!sess) throw new Error("Invalid session token.");
  sess.tier = tier;
  sess.updated_at = nowIso();
  sessionsByToken.set(token, sess);
  return sess;
}

export function buildSignalsFeed(tier: PlanTier, limit: number): SignalsFeedResponse {
  const plan = getPlan(tier);
  const now = Math.floor(Date.now() / 1000);

  if (tier === "free") {
    return {
      tier,
      mode: "signals_only",
      signal_delay_seconds: plan.limits.signal_delay_seconds,
      signals: [],
      generated_at: nowIso(),
    };
  }

  const samples = [
    { symbol: "AAPL", side: "NEUTRAL_BIAS", confidence: 0.58, rationale: "Volatility elevated; confirmation insufficient." },
    { symbol: "MSFT", side: "NEUTRAL_BIAS", confidence: 0.62, rationale: "Trend persistence weak; maintain neutrality." },
    { symbol: "NVDA", side: "BEARISH_BIAS", confidence: 0.66, rationale: "Correlation risk rising; reduced concentration exposure indicated." },
    { symbol: "SPY", side: "NEUTRAL_BIAS", confidence: 0.55, rationale: "Regime neutral; exposure should remain selective." },
    { symbol: "TLT", side: "BULLISH_BIAS", confidence: 0.60, rationale: "Defensive hedging demand present; liquidity acceptable." },
  ];

  const n = Math.max(0, Math.min(limit, samples.length, plan.limits.max_signals_per_response || samples.length));

  const signals = samples.slice(0, n).map((s, i) => ({
    id: `sig_${randomUUID().slice(0, 8)}`,
    ts: now - i * 45,
    status: "published",
    execution_mode: "manual_only",
    symbol: s.symbol,
    side: s.side,
    qty: 0,
    strategy_id: "dev_stub",
    confidence: s.confidence,
    rationale: s.rationale,
    blocked: false,
    reasons: [],
  }));

  return {
    tier,
    mode: "signals_only",
    signal_delay_seconds: plan.limits.signal_delay_seconds,
    signals,
    generated_at: nowIso(),
  };
}
