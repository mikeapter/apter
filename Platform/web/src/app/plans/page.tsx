"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "../../lib/api";

type Plan = {
  tier: string;
  name: string;
  price_usd_month: number;
};

type PlansResponse = {
  plans?: Plan[];
};

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [currentTier, setCurrentTier] = useState<string>("Observer");
  const [globalError, setGlobalError] = useState<string>("");
  const [authWarning, setAuthWarning] = useState<string>("");
  const [signalsWarning, setSignalsWarning] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);

  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");

  const tokenKey = "apter_token";

  async function loadPage() {
    setLoading(true);
    setGlobalError("");
    setAuthWarning("");
    setSignalsWarning("");

    try {
      // REQUIRED endpoint
      const plansRes = await fetchJson<PlansResponse>("/api/plans");
      setPlans(plansRes?.plans ?? []);

      // OPTIONAL endpoint: me
      try {
        const me = await fetchJson<{ tier?: string; name?: string }>("/api/subscription/me");
        setCurrentTier(me?.tier || me?.name || "Observer");
      } catch {
        setCurrentTier("Observer");
        setAuthWarning("Not logged in. You are browsing as Observer.");
      }

      // OPTIONAL endpoint: signals
      try {
        await fetchJson("/api/signals/feed?limit=5");
      } catch {
        setSignalsWarning("Signals preview unavailable (endpoint not enabled yet).");
      }
    } catch (err: any) {
      setGlobalError(err?.message || "Unable to load plans.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPage();
  }, []);

  async function login() {
    setGlobalError("");

    try {
      const base = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/+$/, "");
      const res = await fetch(`${base}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          username: email,
          password,
        }),
      });

      if (!res.ok) {
        throw new Error("Login failed.");
      }

      const data = await res.json();
      if (data?.access_token) {
        localStorage.setItem(tokenKey, data.access_token);
      }

      await loadPage();
    } catch (err: any) {
      setGlobalError(err?.message || "Login failed.");
    }
  }

  function logout() {
    localStorage.removeItem(tokenKey);
    setCurrentTier("Observer");
    setAuthWarning("Not logged in. You are browsing as Observer.");
  }

  return (
    <div className="p-6 text-white">
      <h1 className="text-4xl font-bold">Subscription Plans</h1>
      <p className="mt-3 text-slate-300">
        Signals-only trading tool. No auto-execution. Plans control access to signals, history, and analytics.
      </p>

      {loading && <p className="mt-4 text-slate-300">Loading…</p>}
      {globalError && <p className="mt-4 text-red-400">{globalError}</p>}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Login */}
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
            <button className="rounded bg-slate-800 px-4 py-2">Register</button>
            <button className="rounded bg-slate-800 px-4 py-2" onClick={login}>
              Login
            </button>
            <button className="rounded bg-slate-800 px-4 py-2" onClick={logout}>
              Logout
            </button>
          </div>

          <div className="mt-3 text-sm text-slate-400">
            Token stored in localStorage key: {tokenKey}
          </div>
        </div>

        {/* Current subscription */}
        <div className="rounded-md border border-slate-800 bg-[#0a1136] p-4">
          <h2 className="text-2xl font-semibold">Current Subscription</h2>
          <div className="mt-3 text-lg">{currentTier}</div>

          {authWarning && <div className="mt-2 text-amber-300">{authWarning}</div>}

          <div className="mt-4 text-sm text-slate-400">
            Used only to switch tiers locally via <code>/api/subscription/dev/set-tier</code>.
          </div>
        </div>

        {/* Signals */}
        <div className="rounded-md border border-slate-800 bg-[#0a1136] p-4">
          <h2 className="text-2xl font-semibold">Signals Preview</h2>

          <button className="mt-3 rounded bg-slate-800 px-4 py-2" onClick={loadPage}>
            Refresh feed
          </button>

          <div className="mt-3 text-sm">
            {signalsWarning ? (
              <span className="text-amber-300">{signalsWarning}</span>
            ) : (
              <span className="text-slate-400">Signals feed ready.</span>
            )}
          </div>
        </div>
      </div>

      {/* Plans */}
      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {plans.map((p) => (
          <div key={p.tier} className="rounded border border-slate-800 bg-[#0a1136] p-4">
            <div className="text-sm text-slate-400">{p.tier}</div>
            <div className="text-xl font-semibold">{p.name}</div>
            <div className="text-slate-200">${p.price_usd_month}/month</div>
          </div>
        ))}
      </div>

      <p className="mt-6 text-sm text-slate-400">
        Note: "Alerts" and "payments" are not implemented in Step 1; this page verifies plan definitions and server-side gating.
      </p>
    </div>
  );
}
