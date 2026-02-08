"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchJson } from "../../lib/api";

type Plan = {
  tier: string;
  name: string;
  price_usd_month: number;
};

type PlansResponse = { plans?: Plan[] };

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function retry<T>(fn: () => Promise<T>, attempts = 3, delayMs = 1200): Promise<T> {
  let lastErr: unknown;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (e) {
      lastErr = e;
      if (i < attempts - 1) await sleep(delayMs);
    }
  }
  throw lastErr;
}

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [currentTier, setCurrentTier] = useState("Observer");
  const [globalNotice, setGlobalNotice] = useState("");
  const [authNotice, setAuthNotice] = useState("");
  const [signalsNotice, setSignalsNotice] = useState("");
  const [loading, setLoading] = useState(true);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const tokenKey = "apter_token";

  const loadPage = useCallback(async () => {
    setLoading(true);
    setGlobalNotice("");
    setAuthNotice("");
    setSignalsNotice("");

    // 1) REQUIRED: plans (with retry for cold-start)
    try {
      const plansRes = await retry(() => fetchJson<PlansResponse>("/api/plans"), 4, 1500);
      setPlans(plansRes?.plans ?? []);
    } catch {
      setPlans([]);
      setGlobalNotice("Plans service is waking up. Please refresh in ~10–20 seconds.");
      setLoading(false);
      return; // stop here; page still renders safely
    }

    // 2) OPTIONAL: current subscription
    try {
      const me = await retry(() => fetchJson<{ tier?: string; name?: string }>("/api/subscription/me"), 2, 900);
      setCurrentTier(me?.tier || me?.name || "Observer");
    } catch {
      setCurrentTier("Observer");
      setAuthNotice("Not logged in. You are browsing as Observer.");
    }

    // 3) OPTIONAL: signals
    try {
      await retry(() => fetchJson("/api/signals/feed?limit=5"), 2, 900);
    } catch {
      setSignalsNotice("Signals preview unavailable (endpoint not enabled yet).");
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    loadPage();
  }, [loadPage]);

  async function login() {
    setGlobalNotice("");
    try {
      const base = (process.env.NEXT_PUBLIC_API_BASE_URL || "").replace(/\/+$/, "");
      const res = await fetch(`${base}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: email, password }),
      });

      if (!res.ok) throw new Error("Login request failed");

      const data = await res.json();
      if (data?.access_token) localStorage.setItem(tokenKey, data.access_token);

      await loadPage();
    } catch {
      setGlobalNotice("Login failed. Please verify credentials and try again.");
    }
  }

  function logout() {
    localStorage.removeItem(tokenKey);
    setCurrentTier("Observer");
    setAuthNotice("Not logged in. You are browsing as Observer.");
  }

  return (
    <div className="p-6 text-white">
      <h1 className="text-4xl font-bold">Subscription Plans</h1>
      <p className="mt-3 text-slate-300">
        Signals-only trading tool. No auto-execution. Plans control access to signals, history, and analytics.
      </p>

      {loading && <p className="mt-4 text-slate-300">Loading…</p>}
      {globalNotice && <p className="mt-4 text-amber-300">{globalNotice}</p>}

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
            <button className="rounded bg-slate-800 px-4 py-2">Register</button>
            <button className="rounded bg-slate-800 px-4 py-2" onClick={login}>Login</button>
            <button className="rounded bg-slate-800 px-4 py-2" onClick={logout}>Logout</button>
          </div>
          <div className="mt-3 text-sm text-slate-400">Token stored in localStorage key: {tokenKey}</div>
        </div>

        <div className="rounded-md border border-slate-800 bg-[#0a1136] p-4">
          <h2 className="text-2xl font-semibold">Current Subscription</h2>
          <div className="mt-3 text-lg">{currentTier}</div>
          {authNotice && <div className="mt-2 text-amber-300">{authNotice}</div>}
          <div className="mt-4 text-sm text-slate-400">
            Used only to switch tiers locally via <code>/api/subscription/dev/set-tier</code>.
          </div>
        </div>

        <div className="rounded-md border border-slate-800 bg-[#0a1136] p-4">
          <h2 className="text-2xl font-semibold">Signals Preview</h2>
          <button className="mt-3 rounded bg-slate-800 px-4 py-2" onClick={loadPage}>Refresh feed</button>
          <div className="mt-3 text-sm">
            {signalsNotice ? (
              <span className="text-amber-300">{signalsNotice}</span>
            ) : (
              <span className="text-slate-400">Signals feed ready.</span>
            )}
          </div>
        </div>
      </div>

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
