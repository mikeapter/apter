"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchJson } from "../../lib/api";

type Plan = {
  tier: string;
  name: string;
  price_usd_month: number;
  target_user?: string;
};

type PlansResponse = { plans?: Plan[] };

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [currentTier, setCurrentTier] = useState("Observer");
  const [loading, setLoading] = useState(true);

  // Only for truly blocking failures (like /api/plans)
  const [globalError, setGlobalError] = useState("");

  // Optional warnings
  const [signalsWarning, setSignalsWarning] = useState("");
  const [authWarning, setAuthWarning] = useState("");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const tokenKey = "apter_token";

  const loadPage = useCallback(async () => {
    setLoading(true);
    setGlobalError("");
    setSignalsWarning("");
    setAuthWarning("");

    try {
      // REQUIRED: plans must load
      const plansRes = await fetchJson<PlansResponse>("/api/plans");
      setPlans(plansRes?.plans ?? []);

      // OPTIONAL: current tier from auth endpoint
      try {
        const me = await fetchJson<{ tier?: string; name?: string }>("/api/subscription/me");
        setCurrentTier(me?.tier || me?.name || "Observer");
      } catch {
        setCurrentTier("Observer");
        setAuthWarning("Login required to load current subscription.");
      }

      // OPTIONAL: signals preview (endpoint may not exist yet)
      try {
        await fetchJson("/api/signals/feed?limit=5");
      } catch {
        setSignalsWarning("Signals preview unavailable until /api/signals/feed is enabled.");
      }
    } catch (err: any) {
      setGlobalError(err?.message || "Failed to fetch plans");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPage();
  }, [loadPage]);

  async function register() {
    setGlobalError("");
    try {
      await fetchJson("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      await login();
    } catch (err: any) {
      setGlobalError(err?.message || "Register failed");
    }
  }

  async function login() {
    setGlobalError("");
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
      await loadPage();
    } catch (err: any) {
      setGlobalError(err?.message || "Login failed");
    }
  }

  function logout() {
    localStorage.removeItem(tokenKey);
    setCurrentTier("Observer");
    setAuthWarning("Logged out.");
  }

  return (
    <div className="p-6 text-white">
      <h1 className="text-4xl font-bold">Subscription Plans</h1>
      <p className="mt-3 text-slate-300">
        Signals-only trading tool. No auto-execution. Plans control access to signals, history, and analytics.
      </p>

      {loading && <p className="mt-4 text-slate-300">Loading…</p>}
      {globalError && <p className="mt-4 text-red-400">{globalError}</p>}
      {authWarning && <p className="mt-2 text-amber-300">{authWarning}</p>}
      {signalsWarning && <p className="mt-2 text-amber-300">{signalsWarning}</p>}

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
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
          <div className="mt-3 text-sm text-slate-400">Token key: {tokenKey}</div>
        </div>

        <div className="rounded-md border border-slate-800 bg-[#0a1136] p-4">
          <h2 className="text-2xl font-semibold">Current Subscription</h2>
          <div className="mt-3 text-lg">{currentTier}</div>
        </div>

        <div className="rounded-md border border-slate-800 bg-[#0a1136] p-4">
          <h2 className="text-2xl font-semibold">Signals Preview</h2>
          <div className="mt-3 text-slate-400">
            Endpoint checked on load. Add /api/signals/feed to enable live preview.
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {plans.map((p) => (
          <div key={p.tier} className="rounded border border-slate-800 bg-[#0a1136] p-4">
            <div className="text-sm text-slate-400">{p.tier}</div>
            <div className="text-xl font-semibold">{p.name}</div>
            <div className="text-slate-200">${p.price_usd_month}/month</div>
            {p.target_user && <div className="mt-1 text-sm text-slate-400">{p.target_user}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
