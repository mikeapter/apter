"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { COMPLIANCE } from "../../lib/compliance";

type PlanTier = "free" | "standard" | "pro";

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

  useEffect(() => {
    refreshMe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const currentTier: PlanTier = useMemo(() => {
    if (me?.tier) return me.tier;
    return "free";
  }, [me]);

  async function doRegister() {
    setAuthMsg("");
    const r = await apiPost<RegisterResponse>("/auth/register", { email, password });
    if (!r.ok) return setAuthMsg(r.error);
    setToken(r.data.access_token);
    try {
      localStorage.setItem(LS_TOKEN, r.data.access_token);
    } catch {}
    setAuthMsg(`Registered: ${r.data.email} (Free tier)`);
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
        <div className="text-muted-foreground text-sm">
          Choose the analytics tier that fits your research needs. All tiers include the institutional-quality dashboard.
        </div>
      </div>

      {/* Plan cards */}
      <div className="grid gap-4 lg:grid-cols-3">
        {plansError ? (
          <div className="text-red-400 col-span-3">{plansError}</div>
        ) : plans.length === 0 ? (
          <div className="text-muted-foreground col-span-3 text-sm">Loading plans...</div>
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

      {/* Dev tools */}
      <details className="bt-panel">
        <summary className="px-4 py-3 cursor-pointer text-sm font-semibold text-muted-foreground hover:text-foreground">
          Dev Tools (Auth &amp; Tier Switching)
        </summary>
        <div className="px-4 pb-4 border-t border-border pt-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <div className="font-semibold text-sm mb-2">Login / Register (Dev)</div>
              <div className="space-y-2">
                <input
                  className="bt-input"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
                <input
                  className="bt-input"
                  placeholder="Password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <div className="flex gap-2">
                  <button className="bt-button h-10 px-4" onClick={doRegister}>Register</button>
                  <button className="bt-button h-10 px-4" onClick={doLogin}>Login</button>
                  <button className="bt-button h-10 px-4" onClick={doLogout}>Logout</button>
                </div>
                {!!authMsg && <div className="text-sm">{authMsg}</div>}
              </div>
            </div>

            <div>
              <div className="font-semibold text-sm mb-2">Current Subscription</div>
              {!token ? (
                <div className="text-sm text-muted-foreground">
                  Not logged in. Browsing as <span className="font-semibold">Free</span>.
                </div>
              ) : me ? (
                <div className="text-sm space-y-1">
                  <div>Tier: <span className="font-semibold">{me.tier.toUpperCase()}</span></div>
                  <div>Status: <span className="font-semibold">{me.status}</span></div>
                  <div className="text-xs text-muted-foreground">Updated: {me.updated_at}</div>
                </div>
              ) : meError ? (
                <div className="text-sm text-red-400">{meError}</div>
              ) : (
                <div className="text-sm text-muted-foreground">Loading...</div>
              )}

              <div className="mt-4">
                <div className="font-semibold text-sm mb-2">Dev Admin Key</div>
                <input
                  className="bt-input"
                  placeholder="X-Admin-Key (LOCAL_DEV_API_KEY)"
                  value={adminKey}
                  onChange={(e) => saveAdminKey(e.target.value)}
                />
                <div className="text-xs text-muted-foreground mt-1">
                  Used only to switch tiers locally.
                </div>
              </div>
            </div>
          </div>
        </div>
      </details>

      <div className="text-xs text-muted-foreground">
        {COMPLIANCE.NOT_INVESTMENT_ADVICE}
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
  onSelect: () => void | Promise<void>;
  canSelect: boolean;
}) {
  const price = plan.price_usd_month === 0 ? "Free" : `$${plan.price_usd_month}/mo`;
  const highlight = plan.tier === "standard";

  return (
    <div className={`bt-panel p-4 flex flex-col ${highlight ? "ring-1 ring-[hsl(var(--risk-on))]/40" : ""}`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xl font-semibold">{plan.name}</div>
          <div className="text-muted-foreground text-sm mt-0.5">{plan.target_user}</div>
        </div>
        <div className="text-lg font-bold font-mono">{price}</div>
      </div>

      <div className="mt-4">
        <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-2">Included</div>
        <ul className="text-sm text-muted-foreground space-y-1 list-disc pl-5">
          {plan.features.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      </div>

      {plan.exclusions.length > 0 && plan.exclusions[0] !== "None — full platform access" && (
        <div className="mt-4">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-2">Not Included</div>
          <ul className="text-sm text-muted-foreground space-y-1 list-disc pl-5">
            {plan.exclusions.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}

      {plan.exclusions[0] === "None — full platform access" && (
        <div className="mt-4 text-sm text-[hsl(var(--risk-on))] font-medium">Full platform access</div>
      )}

      <div className="mt-4 flex-1" />
      <button
        className={`bt-button h-11 w-full mt-4 ${isCurrent ? "opacity-60 cursor-default" : ""}`}
        onClick={onSelect}
        disabled={!canSelect || isCurrent}
        title={!canSelect ? "Login to enable dev tier switching" : isCurrent ? "Current plan" : ""}
      >
        {isCurrent ? "Current Plan" : `Select ${plan.name}`}
      </button>
    </div>
  );
}
