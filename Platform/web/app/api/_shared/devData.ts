import { randomUUID } from "crypto";

export type PlanTier = "observer" | "signals" | "pro";

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
  return v === "observer" || v === "signals" || v === "pro";
}

const PLANS: Plan[] = [
  {
    tier: "observer",
    name: "Observer",
    price_usd_month: 0,
    target_user: "Read-only review of system posture and delayed signals.",
    features: [
      "Market regime status bar",
      "System assessment memorandum",
      "Delayed signal visibility",
      "Limited history visibility",
    ],
    exclusions: ["Real-time feed", "Priority diagnostics", "Extended history", "Alerts"],
    limits: {
      signal_delay_seconds: 86400, // 24h
      max_signals_per_response: 0,
      history_days: 7,
      alerts: false,
    },
  },
  {
    tier: "signals",
    name: "Signals",
    price_usd_month: 9,
    target_user: "Timely signal access with standard diagnostics.",
    features: [
      "Timely signals feed",
      "System history panel",
      "Standard risk diagnostics",
      "Expanded history access",
    ],
    exclusions: ["Premium diagnostics depth", "Advanced analytics exports", "Alerts"],
    limits: {
      signal_delay_seconds: 300, // 5m
      max_signals_per_response: 25,
      history_days: 30,
      alerts: false,
    },
  },
  {
    tier: "pro",
    name: "Pro",
    price_usd_month: 29,
    target_user: "Full diagnostics context and minimal latency on signals.",
    features: [
      "Near real-time signals feed",
      "Full diagnostics panel depth",
      "Extended history access",
      "Priority refresh cadence",
    ],
    exclusions: ["Payments/alerts (not implemented yet)"],
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
  if (!token) return "observer";
  const sess = sessionsByToken.get(token);
  return sess?.tier ?? "observer";
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
    tier: "observer",
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
    tier: "observer",
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

  // Observer: show nothing (consistent with “24h delay” policy)
  if (tier === "observer") {
    return {
      tier,
      mode: "signals_only",
      signal_delay_seconds: plan.limits.signal_delay_seconds,
      signals: [],
      generated_at: nowIso(),
    };
  }

  const samples = [
    { symbol: "AAPL", side: "HOLD", confidence: 0.58, rationale: "Volatility elevated; confirmation insufficient." },
    { symbol: "MSFT", side: "HOLD", confidence: 0.62, rationale: "Trend persistence weak; maintain neutrality." },
    { symbol: "NVDA", side: "SELL", confidence: 0.66, rationale: "Correlation risk rising; reduce concentration exposure." },
    { symbol: "SPY", side: "HOLD", confidence: 0.55, rationale: "Regime neutral; exposure should remain selective." },
    { symbol: "TLT", side: "BUY", confidence: 0.60, rationale: "Risk-off hedging demand present; liquidity acceptable." },
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
