// Platform/web/src/app/plans/page.tsx
"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  API_BASE_URL,
  devSetTier,
  getMySubscription,
  getPlans,
  getSignalsFeed,
  login,
  register,
} from "@/lib/api";

type AnyObj = Record<string, any>;

export default function PlansPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [adminKey, setAdminKey] = useState("dev");

  const [token, setToken] = useState<string>("");
  const [plans, setPlans] = useState<AnyObj | null>(null);
  const [subscription, setSubscription] = useState<AnyObj | null>(null);
  const [signals, setSignals] = useState<AnyObj | null>(null);

  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string>("");

  useEffect(() => {
    const t = localStorage.getItem("apter_token") || "";
    setToken(t);
  }, []);

  const authed = useMemo(() => !!token, [token]);

  async function loadPlansAndSignals(currentToken?: string) {
    setMsg("");
    try {
      const p = await getPlans();
      setPlans(p as AnyObj);
    } catch (e: any) {
      setPlans({ error: e?.message || "Failed to load plans" });
    }

    try {
      const s = await getSignalsFeed(5, currentToken || token || undefined);
      setSignals(s as AnyObj);
    } catch (e: any) {
      setSignals({ error: e?.message || "Failed to load signals" });
    }
  }

  async function loadSubscription(currentToken?: string) {
    const t = currentToken || token;
    if (!t) {
      setSubscription({ detail: "Not authenticated" });
      return;
    }
    try {
      const sub = await getMySubscription(t);
      setSubscription(sub as AnyObj);
    } catch (e: any) {
      setSubscription({ error: e?.message || "Failed to load subscription" });
    }
  }

  useEffect(() => {
    loadPlansAndSignals(token || undefined);
    loadSubscription(token || undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function onRegister() {
    setLoading(true);
    setMsg("");
    try {
      await register(email, password);
      setMsg("Registered successfully. Now click Login.");
    } catch (e: any) {
      setMsg(e?.message || "Register failed");
    } finally {
      setLoading(false);
    }
  }

  async function onLogin() {
    setLoading(true);
    setMsg("");
    try {
      const res = (await login(email, password)) as AnyObj;
      const t = res?.access_token || res?.token;
      if (!t) throw new Error("No access token returned");
      localStorage.setItem("apter_token", t);
      setToken(t);
      setMsg("Login successful.");
    } catch (e: any) {
      setMsg(e?.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  function onLogout() {
    localStorage.removeItem("apter_token");
    setToken("");
    setSubscription({ detail: "Not authenticated" });
    setMsg("Logged out.");
  }

  async function onSetTier(tier: "free" | "analyst" | "pro") {
    if (!token) {
      setMsg("Login first.");
      return;
    }
    setLoading(true);
    setMsg("");
    try {
      await devSetTier(token, tier, adminKey);
      await loadSubscription(token);
      setMsg(`Tier switched to ${tier.toUpperCase()}.`);
    } catch (e: any) {
      setMsg(e?.message || "Tier switch failed");
    } finally {
      setLoading(false);
    }
  }

  async function onRefreshFeed() {
    setLoading(true);
    setMsg("");
    try {
      const s = await getSignalsFeed(5, token || undefined);
      setSignals(s as AnyObj);
      setMsg("Feed refreshed.");
    } catch (e: any) {
      setMsg(e?.message || "Refresh failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 text-white">
      <h1 className="text-3xl font-semibold mb-2">Subscription Plans</h1>
      <p className="text-sm opacity-80 mb-6">
        Signals-only trading tool. No auto-execution. Plans control access to signals, history, and analytics.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <section className="border border-slate-700 rounded-xl p-4 bg-slate-900/40">
          <h2 className="text-xl mb-3">Login / Register (Dev)</h2>
          <input
            className="w-full mb-2 px-3 py-2 rounded bg-slate-950 border border-slate-700"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password"
            className="w-full mb-3 px-3 py-2 rounded bg-slate-950 border border-slate-700"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <div className="flex gap-2 mb-3">
            <button className="px-3 py-2 rounded border border-slate-600" onClick={onRegister} disabled={loading}>
              Register
            </button>
            <button className="px-3 py-2 rounded border border-slate-600" onClick={onLogin} disabled={loading}>
              Login
            </button>
            <button className="px-3 py-2 rounded border border-slate-600" onClick={onLogout} disabled={loading}>
              Logout
            </button>
          </div>
          <p className="text-xs opacity-70">Token stored in localStorage key: apter_token</p>
          <p className="text-xs opacity-70 mt-2">API base: {API_BASE_URL}</p>
        </section>

        <section className="border border-slate-700 rounded-xl p-4 bg-slate-900/40">
          <h2 className="text-xl mb-3">Current Subscription</h2>
          <pre className="text-sm whitespace-pre-wrap break-words">
            {JSON.stringify(subscription, null, 2)}
          </pre>

          <h3 className="text-lg mt-4 mb-2">Dev Admin Key</h3>
          <input
            className="w-full mb-3 px-3 py-2 rounded bg-slate-950 border border-slate-700"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
          />
          <div className="flex gap-2 flex-wrap">
            <button className="px-3 py-2 rounded border border-slate-600" onClick={() => onSetTier("free")} disabled={!authed || loading}>FREE</button>
            <button className="px-3 py-2 rounded border border-slate-600" onClick={() => onSetTier("analyst")} disabled={!authed || loading}>ANALYST</button>
            <button className="px-3 py-2 rounded border border-slate-600" onClick={() => onSetTier("pro")} disabled={!authed || loading}>PRO</button>
          </div>
        </section>

        <section className="border border-slate-700 rounded-xl p-4 bg-slate-900/40">
          <h2 className="text-xl mb-3">Signals Preview</h2>
          <button className="px-3 py-2 rounded border border-slate-600 mb-3" onClick={onRefreshFeed} disabled={loading}>
            Refresh feed
          </button>
          <pre className="text-sm whitespace-pre-wrap break-words">
            {JSON.stringify(signals, null, 2)}
          </pre>
        </section>
      </div>

      <section className="border border-slate-700 rounded-xl p-4 bg-slate-900/40 mt-4">
        <h2 className="text-xl mb-3">Plan Definitions</h2>
        <pre className="text-sm whitespace-pre-wrap break-words">
          {JSON.stringify(plans, null, 2)}
        </pre>
      </section>

      {msg ? <p className="mt-4 text-sm text-rose-300">{msg}</p> : null}
    </div>
  );
}
