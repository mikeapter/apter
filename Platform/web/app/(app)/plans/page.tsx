"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

type PlanTier = "observer" | "signals" | "pro";

type Plan = {
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

type PlansResponse = {
  plans: Plan[];
  as_of: string;
};

type RegisterResponse = {
  user_id: number;
  email: string;
  access_token: string;
  token_type: string;
};

type LoginResponse =
  | { requires_2fa: true; user_id: number; message: string }
  | { access_token: string; token_type: string };

type SubscriptionMeResponse = {
  tier: PlanTier;
  plan: Plan;
  status: string;
  updated_at: string;
};

type SignalsFeedResponse = {
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

const LS_TOKEN = "apter_token";
const LS_ADMIN_KEY = "apter_admin_key";

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [plansError, setPlansError] = useState<string | null>(null);

  const [token, setToken] = useState<string>("");
  const [adminKey, setAdminKey] = useState<string>("");

  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [authMsg, setAuthMsg] = useState<string>("");

  const [me, setMe] = useState<SubscriptionMeResponse | null>(null);
  const [meError, setMeError] = useState<string | null>(null);

  const [feed, setFeed] = useState<SignalsFeedResponse | null>(null);
  const [feedError, setFeedError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const t = localStorage.getItem(LS_TOKEN) || "";
      const k = localStorage.getItem(LS_ADMIN_KEY) || "";
      setToken(t);
      setAdminKey(k);
    } catch {}
  }, []);

  useEffect(() => {
    (async () => {
      const r = await apiGet<PlansResponse>("/api/plans");
      if (!r.ok) {
        setPlansError(r.error);
        return;
      }
      setPlans(r.data.plans);
    })();
  }, []);

  async function refreshMe() {
    setMeError(null);
    setMe(null);
    if (!token) return;
    const r = await apiGet<SubscriptionMeResponse>("/api/subscription/me", undefined, token);
    if (!r.ok) {
      setMeError(r.error);
      return;
    }
    setMe(r.data);
  }

  async function refreshFeed() {
    setFeedError(null);
    setFeed(null);
    const r = await apiGet<SignalsFeedResponse>("/v1/signals/feed?limit=25", undefined, token || undefined);
    if (!r.ok) {
      setFeedError(r.error);
      return;
    }
    setFeed(r.data);
  }

  useEffect(() => {
    refreshMe();
    refreshFeed();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const currentTier: PlanTier = useMemo(() => {
    if (me?.tier) return me.tier;
    return "observer";
  }, [me]);

  async function doRegister() {
    setAuthMsg("");
    const r = await apiPost<RegisterResponse>("/auth/register", { email, password });
    if (!r.ok) return setAuthMsg(r.error);
    setToken(r.data.access_token);
    try {
      localStorage.setItem(LS_TOKEN, r.data.access_token);
    } catch {}
    setAuthMsg(`Registered: ${r.data.email} (Observer tier)`);
  }

  async function doLogin() {
    setAuthMsg("");
    const r = await apiPost<LoginResponse>("/auth/login", { email, password });
    if (!r.ok) return setAuthMsg(r.error);
    if ((r.data as any).requires_2fa) {
      setAuthMsg("2FA is enabled for this account. Use the /auth/login/2fa endpoint for now.");
      return;
    }
    const access_token = (r.data as any).access_token as string;
    setToken(access_token);
    try {
      localStorage.setItem(LS_TOKEN, access_token);
    } catch {}
    setAuthMsg("Logged in.");
  }

  function doLogout() {
    setToken("");
    setMe(null);
    try {
      localStorage.removeItem(LS_TOKEN);
    } catch {}
  }

  async function setTier(tier: PlanTier) {
    if (!token) {
      setAuthMsg("Login first to set tier (dev switch).");
      return;
    }
    if (!adminKey) {
      setAuthMsg("Enter your X-Admin-Key (LOCAL_DEV_API_KEY) to set tier.");
      return;
    }

    const r = await apiPost<{ ok: boolean; tier: PlanTier; status: string }>(
      "/api/subscription/dev/set-tier",
      { tier },
      { headers: { "X-Admin-Key": adminKey } },
      token
    );

    if (!r.ok) {
      setAuthMsg(r.error);
      return;
    }

    setAuthMsg(`Tier set to: ${r.data.tier}`);
    await refreshMe();
    await refreshFeed();
  }

  function saveAdminKey(v: string) {
    setAdminKey(v);
    try {
      if (v) localStorage.setItem(LS_ADMIN_KEY, v);
      else localStorage.removeItem(LS_ADMIN_KEY);
    } catch {}
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <div className="text-2xl font-semibold">Subscription Plans</div>
        <div className="text-muted-foreground">
          Signals-only trading tool. No auto-execution. Plans control access to signals, history, and analytics.
        </div>
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <div className="font-semibold mb-2">Login / Register (Dev)</div>
            <div className="space-y-2">
              <input
                className="w-full h-10 rounded-md border border-border bg-background px-3 text-sm"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <input
                className="w-full h-10 rounded-md border border-border bg-background px-3 text-sm"
                placeholder="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <div className="flex gap-2">
                <button
                  className="h-10 px-3 rounded-md border border-border hover:bg-muted text-sm font-semibold"
                  onClick={doRegister}
                >
                  Register
                </button>
                <button
                  className="h-10 px-3 rounded-md border border-border hover:bg-muted text-sm font-semibold"
                  onClick={doLogin}
                >
                  Login
                </button>
                <button
                  className="h-10 px-3 rounded-md border border-border hover:bg-muted text-sm font-semibold"
                  onClick={doLogout}
                >
                  Logout
                </button>
              </div>
              <div className="text-xs text-muted-foreground">
                Token stored in localStorage key: <span className="font-mono">{LS_TOKEN}</span>
              </div>
              {!!authMsg && <div className="text-sm">{authMsg}</div>}
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="font-semibold mb-2">Current Subscription</div>
            {!token ? (
              <div className="text-sm text-muted-foreground">
                Not logged in. You are browsing as <span className="font-semibold">Observer</span>.
              </div>
            ) : me ? (
              <div className="text-sm space-y-1">
                <div>
                  Tier: <span className="font-semibold">{me.tier.toUpperCase()}</span>
                </div>
                <div>
                  Status: <span className="font-semibold">{me.status}</span>
                </div>
                <div className="text-xs text-muted-foreground">Updated: {me.updated_at}</div>
              </div>
            ) : meError ? (
              <div className="text-sm text-red-400">{meError}</div>
            ) : (
              <div className="text-sm text-muted-foreground">Loading…</div>
            )}

            <div className="mt-4">
              <div className="font-semibold mb-2">Dev Admin Key</div>
              <input
                className="w-full h-10 rounded-md border border-border bg-background px-3 text-sm"
                placeholder="X-Admin-Key (LOCAL_DEV_API_KEY)"
                value={adminKey}
                onChange={(e) => saveAdminKey(e.target.value)}
              />
              <div className="text-xs text-muted-foreground mt-1">
                Used only to switch tiers locally via <span className="font-mono">/api/subscription/dev/set-tier</span>.
              </div>
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="font-semibold mb-2">Signals Preview</div>
            <button
              className="h-10 px-3 rounded-md border border-border hover:bg-muted text-sm font-semibold"
              onClick={refreshFeed}
            >
              Refresh feed
            </button>
            {feedError ? (
              <div className="mt-3 text-sm text-red-400">{feedError}</div>
            ) : feed ? (
              <div className="mt-3 text-sm">
                <div className="text-muted-foreground">
                  Mode: <span className="font-semibold">{feed.mode}</span> · Tier: {feed.tier}
                </div>
                <div className="mt-2 space-y-2">
                  {feed.signals.length === 0 ? (
                    <div className="text-muted-foreground">No eligible signals (Observer has 24h delay).</div>
                  ) : (
                    feed.signals.map((s, i) => (
                      <div key={s.id || i} className="rounded-md border border-border p-2">
                        <div className="flex items-center justify-between">
                          <div className="font-semibold">
                            {s.symbol} · {s.side}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {s.ts ? new Date(s.ts * 1000).toISOString() : ""}
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Conf: {typeof s.confidence === "number" ? s.confidence.toFixed(2) : "—"} ·{" "}
                          {s.rationale || ""}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <div className="mt-3 text-sm text-muted-foreground">Loading…</div>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {plansError ? (
          <div className="text-red-400">{plansError}</div>
        ) : (
          plans.map((p) => (
            <PlanCard
              key={p.tier}
              plan={p}
              isCurrent={p.tier === currentTier}
              onSelect={() => setTier(p.tier)}
              canSelect={!!token}
            />
          ))
        )}
      </div>

      <div className="text-xs text-muted-foreground">
        Note: "Alerts" and "payments" are not implemented in Step 1; this page verifies plan definitions and server-side gating.
      </div>
    </div>
  );
}

function PlanCard({
  plan,
  isCurrent,
  onSelect,
  canSelect,
}: {
  plan: Plan;
  isCurrent: boolean;
  onSelect: () => void;
  canSelect: boolean;
}) {
  const price = plan.price_usd_month === 0 ? "Free" : `$${plan.price_usd_month}/mo`;
  return (
    <div className="rounded-lg border border-border bg-card p-4 flex flex-col">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xl font-semibold">{plan.name}</div>
          <div className="text-muted-foreground text-sm">{plan.target_user}</div>
        </div>
        <div className="text-lg font-bold">{price}</div>
      </div>

      <div className="mt-4">
        <div className="text-sm font-semibold mb-2">Included</div>
        <ul className="text-sm text-muted-foreground space-y-1 list-disc pl-5">
          {plan.features.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      </div>

      <div className="mt-4">
        <div className="text-sm font-semibold mb-2">Excluded</div>
        <ul className="text-sm text-muted-foreground space-y-1 list-disc pl-5">
          {plan.exclusions.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      </div>

      <div className="mt-4 text-xs text-muted-foreground">
        Limits: delay {plan.limits.signal_delay_seconds}s · max {plan.limits.max_signals_per_response} signals · history{" "}
        {plan.limits.history_days} days
      </div>

      <div className="mt-4 flex-1" />
      <button
        className={`h-11 rounded-md border border-border text-sm font-semibold hover:bg-muted ${
          isCurrent ? "opacity-60 cursor-default" : ""
        }`}
        onClick={onSelect}
        disabled={!canSelect || isCurrent}
        title={!canSelect ? "Login to enable dev tier switching" : isCurrent ? "Current plan" : ""}
      >
        {isCurrent ? "Current Plan" : "Switch to this tier (Dev)"}
      </button>
    </div>
  );
}
