// Platform/web/src/app/plans/page.tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { devSetTier, getMySubscription, getPlans, getSignalsFeed, login, register } from "@/lib/api";

type Plan = {
  id?: number;
  code?: string;
  name: string;
  description?: string;
  price_monthly?: number;
  realtime?: boolean;
  history_days?: number;
  analytics_level?: string;
};

type FeedItem = {
  symbol?: string;
  action?: string;
  confidence?: string;
  ts?: string;
};

const TOKEN_KEY = "apter_token";

export default function PlansPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [token, setToken] = useState<string | null>(null);
  const [devKey, setDevKey] = useState("dev");

  const [plans, setPlans] = useState<Plan[]>([]);
  const [plansErr, setPlansErr] = useState<string>("");

  const [me, setMe] = useState<any>(null);
  const [meErr, setMeErr] = useState<string>("");

  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [feedErr, setFeedErr] = useState<string>("");

  const isLoggedIn = useMemo(() => !!token, [token]);

  useEffect(() => {
    const t = localStorage.getItem(TOKEN_KEY);
    if (t) setToken(t);
  }, []);

  useEffect(() => {
    loadPlans();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (token) {
      loadMe(token);
      loadFeed(token);
    } else {
      setMe(null);
      setMeErr("Not authenticated");
      setFeed([]);
      setFeedErr("Login required for feed preview");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function loadPlans() {
    setPlansErr("");
    try {
      const data = await getPlans();
      const arr = Array.isArray(data) ? (data as Plan[]) : [];
      setPlans(arr);
    } catch (e: any) {
      setPlans([]);
      setPlansErr(e?.message || "Failed to load plans");
    }
  }

  async function loadMe(t: string) {
    setMeErr("");
    try {
      const data = await getMySubscription(t);
      setMe(data);
    } catch (e: any) {
      setMe(null);
      setMeErr(e?.message || "Failed to load current subscription");
    }
  }

  async function loadFeed(t: string) {
    setFeedErr("");
    try {
      const data: any = await getSignalsFeed(5, t);
      const items = Array.isArray(data) ? data : data?.items || [];
      setFeed(items);
    } catch (e: any) {
      setFeed([]);
      setFeedErr(e?.message || "Failed to load feed");
    }
  }

  async function onRegister() {
    try {
      await register(email.trim(), password);
      alert("Registered. Now click Login.");
    } catch (e: any) {
      alert(e?.message || "Register failed");
    }
  }

  async function onLogin() {
    try {
      const out = await login(email.trim(), password);
      const t = out?.access_token;
      if (!t) throw new Error("No token returned");
      localStorage.setItem(TOKEN_KEY, t);
      setToken(t);
    } catch (e: any) {
      alert(e?.message || "Login failed");
    }
  }

  function onLogout() {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
  }

  async function onSwitchTier(nextTier: string) {
    if (!token) {
      alert("Login first");
      return;
    }
    try {
      await devSetTier(nextTier, devKey, token);
      await loadMe(token);
      await loadFeed(token);
      alert(`Tier switched to ${nextTier}`);
    } catch (e: any) {
      alert(e?.message || "Tier switch failed");
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold">Subscription Plans</h1>
      <p className="text-sm opacity-80">
        Signals-only trading tool. No auto-execution. Plans control access to signals, history, and analytics.
      </p>

      <div className="grid gap-6 md:grid-cols-3">
        <section className="rounded-2xl border p-4 space-y-3">
          <h2 className="text-xl font-semibold">Login / Register (Dev)</h2>
          <input
            className="w-full rounded border bg-transparent px-3 py-2"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className="w-full rounded border bg-transparent px-3 py-2"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <div className="flex gap-2">
            <button className="rounded border px-4 py-2" onClick={onRegister}>Register</button>
            <button className="rounded border px-4 py-2" onClick={onLogin}>Login</button>
            <button className="rounded border px-4 py-2" onClick={onLogout}>Logout</button>
          </div>
          <p className="text-xs opacity-70">Token stored in localStorage key: {TOKEN_KEY}</p>
        </section>

        <section className="rounded-2xl border p-4 space-y-3">
          <h2 className="text-xl font-semibold">Current Subscription</h2>
          {meErr ? <p className="text-red-400">{meErr}</p> : <pre className="text-xs overflow-auto">{JSON.stringify(me, null, 2)}</pre>}

          <h3 className="font-semibold">Dev Admin Key</h3>
          <input
            className="w-full rounded border bg-transparent px-3 py-2"
            value={devKey}
            onChange={(e) => setDevKey(e.target.value)}
          />
          <p className="text-xs opacity-70">Used only to switch tiers locally via /api/subscription/dev/set-tier.</p>

          <div className="flex flex-wrap gap-2">
            <button className="rounded border px-3 py-1" onClick={() => onSwitchTier("observer")} disabled={!isLoggedIn}>Set Observer</button>
            <button className="rounded border px-3 py-1" onClick={() => onSwitchTier("analyst")} disabled={!isLoggedIn}>Set Analyst</button>
            <button className="rounded border px-3 py-1" onClick={() => onSwitchTier("pro")} disabled={!isLoggedIn}>Set Pro</button>
          </div>
        </section>

        <section className="rounded-2xl border p-4 space-y-3">
          <h2 className="text-xl font-semibold">Signals Preview</h2>
          <button className="rounded border px-4 py-2" onClick={() => token && loadFeed(token)} disabled={!isLoggedIn}>
            Refresh feed
          </button>
          {feedErr ? <p className="text-red-400">{feedErr}</p> : <pre className="text-xs overflow-auto">{JSON.stringify(feed, null, 2)}</pre>}
        </section>
      </div>

      <section className="rounded-2xl border p-4">
        <h2 className="text-xl font-semibold mb-3">Available Plans</h2>
        {plansErr ? (
          <p className="text-red-400">{plansErr}</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-3">
            {plans.map((p, idx) => (
              <div key={`${p.code || p.name}-${idx}`} className="rounded-xl border p-3">
                <h3 className="text-lg font-semibold">{p.name}</h3>
                <p className="text-sm opacity-80">{p.description || "No description provided."}</p>
                <ul className="mt-2 text-sm space-y-1 opacity-90">
                  <li>Code: {p.code || "n/a"}</li>
                  <li>Price: {typeof p.price_monthly === "number" ? `$${p.price_monthly}/mo` : "n/a"}</li>
                  <li>Realtime: {String(!!p.realtime)}</li>
                  <li>History days: {p.history_days ?? "n/a"}</li>
                  <li>Analytics: {p.analytics_level ?? "n/a"}</li>
                </ul>
              </div>
            ))}
          </div>
        )}
      </section>

      <p className="text-xs opacity-70">
        Note: "Alerts" and "payments" are not implemented in Step 1; this page verifies plan definitions and server-side gating.
      </p>
    </div>
  );
}
