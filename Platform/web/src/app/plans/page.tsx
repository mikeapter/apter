// Platform/web/src/app/plans/page.tsx
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
const { fetchJson } = api;

type Plan = {
  tier: string;
  name: string;
  price_usd_month: number;
  target_user?: string;
  features?: string[];
  exclusions?: string[];
  limits?: {
    signal_delay_seconds?: number;
    max_signals_per_response?: number;
    history_days?: number;
    alerts?: boolean;
  };
};

type PlansResponse =
  | { plans: Plan[]; as_of?: string }
  | { data?: { plans?: Plan[] } };

type MeResponse = {
  tier?: string;
  name?: string;
};

type Signal = {
  ticker: string;
  signal: string;
  timestamp?: string;
  confidence?: string;
};

type SignalsResponse = { items?: Signal[] } | { signals?: Signal[] };

const PLAN_ENDPOINTS = ["/api/plans", "/api/subscription/plans"];
const ME_ENDPOINTS = ["/api/subscription/me"];
const SIGNAL_ENDPOINTS = ["/api/signals/feed?limit=5", "/api/signals/feed"];

async function firstSuccess<T>(endpoints: string[]): Promise<T> {
  let lastErr: unknown = null;

  for (const ep of endpoints) {
    try {
      return await fetchJson<T>(ep);
    } catch (err) {
      lastErr = err;
    }
  }

  throw lastErr ?? new Error("All endpoints failed");
}

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [currentTier, setCurrentTier] = useState<string>("Unknown");
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [devKey, setDevKey] = useState("dev");

  const tokenKey = "apter_token";

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const plansRes = await firstSuccess<PlansResponse>(PLAN_ENDPOINTS);
      const extractedPlans = Array.isArray((plansRes as any)?.plans)
        ? ((plansRes as any).plans as Plan[])
        : Array.isArray((plansRes as any)?.data?.plans)
        ? (((plansRes as any).data.plans as Plan[]) ?? [])
        : [];
      setPlans(extractedPlans);

      try {
        const me = await firstSuccess<MeResponse>(ME_ENDPOINTS);
        setCurrentTier(me?.tier || me?.name || "Observer");
      } catch {
        setCurrentTier("Observer");
      }

      try {
        const sigRes = await firstSuccess<SignalsResponse>(SIGNAL_ENDPOINTS);
        const items = Array.isArray((sigRes as any)?.items)
          ? ((sigRes as any).items as Signal[])
          : Array.isArray((sigRes as any)?.signals)
          ? ((sigRes as any).signals as Signal[])
          : [];
        setSignals(items);
      } catch {
        setSignals([]);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const planCards = useMemo(() => {
    if (!plans.length) return null;
    return plans.map((p) => (
      <div
        key={p.tier}
        className="rounded-md border border-slate-800 bg-[#0a1136] p-4"
      >
        <div className="text-sm text-slate-300">{p.tier?.toUpperCase()}</div>
        <div className="text-xl font-semibold text-white">{p.name}</div>
        <div className="mt-1 text-slate-200">
          ${p.price_usd_month}
          <span className="text-slate-400"> / month</span>
        </div>
        {p.target_user ? (
          <div className="mt-2 text-sm text-slate-400">{p.target_user}</div>
        ) : null}
      </div>
    ));
  }, [plans]);

  async function register() {
    setError("");
    try {
      await fetchJson("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      await login();
    } catch (err: any) {
      setError(err?.message || "Register failed");
    }
  }

  async function login() {
    setError("");
    try {
      const base = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/+$/, "");
      const url = `${base}/api/auth/login`;

      const body = new URLSearchParams();
      body.set("username", email);
      body.set("password", password);

      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });

      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Login failed: ${res.status} ${txt}`);
      }

      const json = await res.json();
      const token = json?.access_token;
      if (!token) throw new Error("No access token returned");

      localStorage.setItem(tokenKey, token);
      await loadAll();
    } catch (err: any) {
      setError(err?.message || "Login failed");
    }
  }

  function logout() {
    localStorage.removeItem(tokenKey);
    setCurrentTier("Observer");
  }

  async function refreshSignals() {
    setError("");
    try {
      const sigRes = await firstSuccess<SignalsResponse>(SIGNAL_ENDPOINTS);
      const items = Array.isArray((sigRes as any)?.items)
        ? ((sigRes as any).items as Signal[])
        : Array.isArray((sigRes as any)?.signals)
        ? ((sigRes as any).signals as Signal[])
        : [];
      setSignals(items);
    } catch (err: any) {
      setError(err?.message || "Failed to fetch");
    }
  }

  return (
    <div className="p-6 text-white">
      <h1 className="text-4xl font-bold">Subscription Plans</h1>
      <p className="mt-3 text-slate-300">
        Signals-only trading tool. No auto-execution. Plans control access to signals, history, and analytics.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-md border border-slate-800 bg-[#0a1136] p-4">
          <h2 className="text-2xl font-semibold">Login / Register (Dev)</h2>
          <input
            className="mt-4 w-full rounded border border-slate-700 bg-[#070d2b] p-2"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className="mt-2 w-full rounded border border-slate-700 bg-[#070d2b] p-2"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <div className="mt-3 flex gap-2">
            <button className="rounded bg-slate-800 px-4 py-2" onClick={register}>Register</button>
            <button className="rounded bg-slate-800 px-4 py-2" onClick={login}>Login</button>
            <button className="rounded bg-slate-800 px-4 py-2" onClick={logout}>Logout</button>
          </div>
          <div className="mt-3 text-sm text-slate-400">Token stored in localStorage key: {tokenKey}</div>
        </div>

        <div className="rounded-md border border-slate-800 bg-[#0a1136] p-4">
          <h2 className="text-2xl font-semibold">Current Subscription</h2>
          <div className="mt-3 text-lg">{loading ? "Loading..." : currentTier}</div>
          <div className="mt-4">
            <label className="text-sm text-slate-300">Dev Admin Key</label>
            <input
              className="mt-1 w-full rounded border border-slate-700 bg-[#070d2b] p-2"
              value={devKey}
              onChange={(e) => setDevKey(e.target.value)}
            />
            <div className="mt-2 text-sm text-slate-400">
              Used only to switch tiers locally via <code>/api/subscription/dev/set-tier</code>.
            </div>
          </div>
        </div>

        <div className="rounded-md border border-slate-800 bg-[#0a1136] p-4">
          <h2 className="text-2xl font-semibold">Signals Preview</h2>
          <button className="mt-3 rounded bg-slate-800 px-4 py-2" onClick={refreshSignals}>
            Refresh feed
          </button>
          <div className="mt-4 space-y-2">
            {signals.length === 0 ? (
              <div className="text-slate-400">No signals yet.</div>
            ) : (
              signals.map((s, idx) => (
                <div key={`${s.ticker}-${idx}`} className="rounded border border-slate-800 p-2 text-sm">
                  <span className="font-semibold">{s.ticker}</span> — {s.signal}
                  {s.confidence ? ` (${s.confidence})` : ""}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="mt-6">{error ? <div className="text-red-400">{error}</div> : null}</div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">{planCards}</div>

      <p className="mt-6 text-sm text-slate-400">
        Note: "Alerts" and "payments" are not implemented in Step 1; this page verifies plan definitions and server-side gating.
      </p>
    </div>
  );
}
