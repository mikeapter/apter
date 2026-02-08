"use client";

import { useEffect, useState } from "react";
import { fetchJson } from "../../lib/api";

type Plan = {
  tier: string;
  name: string;
  price_usd_month: number;
};

type PlansResponse = { plans?: Plan[] };

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [currentTier, setCurrentTier] = useState("Observer");
  const [signalsWarning, setSignalsWarning] = useState("");
  const [authWarning, setAuthWarning] = useState("");
  const [globalError, setGlobalError] = useState("");
  const [loading, setLoading] = useState(true);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const tokenKey = "apter_token";

  async function loadPage() {
    setLoading(true);
    setGlobalError("");
    setSignalsWarning("");
    setAuthWarning("");

    try {
      // REQUIRED: only this can set globalError
      const plansRes = await fetchJson<PlansResponse>("/api/plans");
      setPlans(plansRes?.plans ?? []);

      // OPTIONAL: auth status
      try {
        const me = await fetchJson<{ tier?: string; name?: string }>("/api/subscription/me");
        setCurrentTier(me?.tier || me?.name || "Observer");
      } catch {
        setCurrentTier("Observer");
        setAuthWarning("Not logged in. You are browsing as Observer.");
      }

      // OPTIONAL: signals preview
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
        body: new URLSearchParams({ username: email, password }),
      });
      if (!res.ok) throw new Error("Login failed.");
      const data = await res.json();
      if (data?.access_token) localStorage.setItem(tokenKey, data.access_token);
      await loadPage();
    } catch (e: any) {
      setGlobalError(e?.message || "Login failed.");
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
            onC
