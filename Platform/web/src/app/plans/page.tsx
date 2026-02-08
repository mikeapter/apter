"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch, ApiError, getApiBaseForDebug } from "@/lib/api";

type Plan = {
  tier: string;
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
  as_of?: string;
};

type MeResponse = {
  tier?: string;
  email?: string;
};

type FeedItem = {
  ticker: string;
  signal: string;
  timestamp?: string;
  confidence?: string;
};

type FeedResponse = {
  items?: FeedItem[];
  signals?: FeedItem[];
};

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [currentTier, setCurrentTier] = useState<string>("(not logged in)");
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorText, setErrorText] = useState<string>("");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [devKey, setDevKey] = useState("dev");

  const dbg = useMemo(() => getApiBaseForDebug(), []);

  async function loadAll() {
    setLoading(true);
    setErrorText("");

    try {
      // 1) plans endpoint (your backend has /api/plans)
      const plansRes = await apiFetch<PlansResponse>("/plans");
      setPlans(Array.isArray(plansRes?.plans) ? plansRes.plans : []);

      // 2) current subscription (requires auth token)
      try {
        const me = await apiFetch<MeResponse>("/subscription/me");
        setCurrentTier(me?.tier || "(unknown)");
      } catch (err) {
        setCurrentTier("(not logged in)");
      }

      // 3) signals preview (may be gated by tier/login)
      try {
        const feedRes = await apiFetch<FeedResponse>("/signals/feed?limit=5");
        const items = Array.isArray(feedRes?.items)
          ? feedRes.items
          : Array.isArray(feedRes?.signals)
          ? feedRes.signals
          : [];
        setFeed(items);
      } catch {
        setFeed([]);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorText(
          [
            `Failed to load plans.`,
            `Status: ${err.status}`,
            `Message: ${err.message}`,
            `Body: ${err.bodyText || "(empty)"}`,
            `API Base RAW: ${dbg.RAW_BASE || "(empty)"}`,
            `API Base normalized: ${dbg.BASE || "(empty)"}`,
          ].join("\n")
        );
      } else {
        setErrorText(
          `Unexpected error while loading plans.\nAPI Base RAW: ${dbg.RAW_BASE || "(empty)"}\nAPI Base normalized: ${dbg.BASE || "(empty)"}`
        );
      }
    } finally {
      setLoading(false);
    }
  }

  async function register() {
    setErrorText("");
    try {
      await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, tier: "observer" }),
      });
      await login();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorText(`Register failed (${err.status}): ${err.bodyText || err.message}`);
      } else {
        setErrorText("Register failed.");
      }
    }
  }

  async function login() {
    setErrorText("");
    try {
      const res = await apiFetch<{ access_token?: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (res?.access_token) {
        localStorage.setItem("apter_token", res.access_token);
      }
      await loadAll();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorText(`Login failed (${err.status}): ${err.bodyText || err.message}`);
      } else {
        setErrorText("Login failed.");
      }
    }
  }

  function logout() {
    localStorage.removeItem("apter_token");
    setCurrentTier("(not logged in)");
  }

  async function setTier(tier: "observer" | "signals" | "pro") {
    setErrorText("");
    try {
      await apiFetch("/subscription/dev/set-tier", {
        method: "POST",
        headers: { "X-Admin-Key": devKey },
        body: JSON.stringify({ tier }),
      });
      await loadAll();
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorText(`Set tier failed (${err.status}): ${err.bodyText || err.message}`);
      } else {
        setErrorText("Set tier failed.");
      }
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="p-6 space-y-6">
      <h1 className="text-3xl font-semibold">Subscription Plans</h1>
      <p className="opacity-80">
        Signals-only trading tool. No auto-execution. Plans control access to signals, history, and analytics.
      </p>

      <div className="grid gap-4 md:grid-cols-3">
        <section className="rounded-xl border p-4 space-y-3">
          <h2 className="font-semibold">Login / Register (Dev)</h2>
          <input
            className="w-full rounded border px-3 py-2 bg-transparent"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className="w-full rounded border px-3 py-2 bg-transparent"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <div className="flex gap-2">
            <button className="rounded border px-3 py-2" onClick={register}>Register</button>
            <button className="rounded border px-3 py-2" onClick={login}>Login</button>
            <button className="rounded border px-3 py-2" onClick={logout}>Logout</button>
          </div>
          <p className="text-sm opacity-70">Token stored in localStorage key: apter_token</p>
        </section>

        <section className="rounded-xl border p-4 space-y-3">
          <h2 className="font-semibold">Current Subscription</h2>
          <p>{loading ? "Loading..." : currentTier}</p>

          <h3 className="font-semibold pt-2">Dev Admin Key</h3>
          <input
            className="w-full rounded border px-3 py-2 bg-transparent"
            value={devKey}
            onChange={(e) => setDevKey(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <button className="rounded border px-3 py-2" onClick={() => setTier("observer")}>Set Observer</button>
            <button className="rounded border px-3 py-2" onClick={() => setTier("signals")}>Set Signals</button>
            <button className="rounded border px-3 py-2" onClick={() => setTier("pro")}>Set Pro</button>
          </div>
        </section>

        <section className="rounded-xl border p-4 space-y-3">
          <h2 className="font-semibold">Signals Preview</h2>
          <button className="rounded border px-3 py-2" onClick={loadAll}>Refresh feed</button>
          <div className="text-sm space-y-1">
            {feed.length === 0 ? (
              <p className="opacity-70">No signals loaded (may be tier-gated or not logged in).</p>
            ) : (
              feed.map((s, i) => (
                <div key={`${s.ticker}-${i}`} className="rounded border px-2 py-1">
                  <strong>{s.ticker}</strong> — {s.signal}
                  {s.confidence ? ` (${s.confidence})` : ""}
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <section className="rounded-xl border p-4">
        <h2 className="font-semibold mb-3">Plan Definitions</h2>
        {loading ? (
          <p>Loading plans…</p>
        ) : plans.length === 0 ? (
          <p className="opacity-70">No plans returned.</p>
        ) : (
          <div className="space-y-3">
            {plans.map((p) => (
              <div key={p.tier} className="rounded border p-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">{p.name}</h3>
                  <span>${p.price_usd_month}/mo</span>
                </div>
                <p className="text-sm opacity-80">Tier: {p.tier} • Target: {p.target_user}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {errorText ? (
        <pre className="whitespace-pre-wrap rounded-xl border p-4 text-red-400">{errorText}</pre>
      ) : null}
    </main>
  );
}
