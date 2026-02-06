"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

type PlansResp = any;
type MeResp = any;
type FeedResp = any;

async function tryGetPlans(): Promise<PlansResp> {
  // Try both route styles in case backend differs by version
  try {
    return await apiGet("/api/subscription/plans", false);
  } catch {
    return await apiGet("/api/subscriptions/plans", false);
  }
}

async function tryGetMe(): Promise<MeResp> {
  try {
    return await apiGet("/api/subscription/me", true);
  } catch {
    return await apiGet("/api/subscriptions/me", true);
  }
}

async function tryGetFeed(): Promise<FeedResp> {
  try {
    return await apiGet("/v1/signals/feed?limit=5", true);
  } catch {
    try {
      return await apiGet("/api/signals/feed?limit=5", true);
    } catch {
      return await apiGet("/v1/signals?limit=5", true);
    }
  }
}

export default function PlansPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [devKey, setDevKey] = useState("dev");

  const [plans, setPlans] = useState<any>(null);
  const [me, setMe] = useState<any>(null);
  const [feed, setFeed] = useState<any>(null);

  const [errPlans, setErrPlans] = useState("");
  const [errMe, setErrMe] = useState("");
  const [errFeed, setErrFeed] = useState("");
  const [authMsg, setAuthMsg] = useState("");

  async function refreshAll() {
    setErrPlans("");
    setErrMe("");
    setErrFeed("");

    try {
      const p = await tryGetPlans();
      setPlans(p);
    } catch (e: any) {
      setErrPlans(e.message || "Failed to fetch plans");
      setPlans(null);
    }

    try {
      const m = await tryGetMe();
      setMe(m);
    } catch (e: any) {
      setErrMe(e.message || "Not authenticated");
      setMe(null);
    }

    try {
      const f = await tryGetFeed();
      setFeed(f);
    } catch (e: any) {
      setErrFeed(e.message || "Failed to fetch feed");
      setFeed(null);
    }
  }

  useEffect(() => {
    refreshAll();
  }, []);

  async function onRegister() {
    setAuthMsg("");
    try {
      const r = await apiPost("/auth/register", { email, password }, false);
      const token = r?.access_token || r?.token;
      if (token) localStorage.setItem("apter_token", token);
      setAuthMsg("Registered successfully.");
      await refreshAll();
    } catch (e: any) {
      setAuthMsg(`Register failed: ${e.message}`);
    }
  }

  async function onLogin() {
    setAuthMsg("");
    try {
      const r = await apiPost("/auth/login", { email, password }, false);
      const token = r?.access_token || r?.token;
      if (!token) throw new Error("No token returned");
      localStorage.setItem("apter_token", token);
      setAuthMsg("Login successful.");
      await refreshAll();
    } catch (e: any) {
      setAuthMsg(`Login failed: ${e.message}`);
    }
  }

  function onLogout() {
    localStorage.removeItem("apter_token");
    setAuthMsg("Logged out.");
    refreshAll();
  }

  async function onSetTier(tier: string) {
    setAuthMsg("");
    try {
      // Local/dev endpoint
      await apiPost(
        "/api/subscription/dev/set-tier",
        { tier },
        true,
        { "X-Admin-Key": devKey }
      );
      setAuthMsg(`Tier updated to ${tier}`);
      await refreshAll();
    } catch (e: any) {
      setAuthMsg(`Set tier failed: ${e.message}`);
    }
  }

  return (
    <main className="p-6 space-y-6">
      <h1 className="text-3xl font-semibold">Subscription Plans</h1>
      <p>Signals-only trading tool. No auto-execution.</p>

      <section className="grid gap-6 md:grid-cols-3">
        <div className="space-y-3 border rounded-xl p-4">
          <h2 className="font-semibold">Login / Register (Dev)</h2>
          <input
            className="w-full border rounded p-2"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className="w-full border rounded p-2"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <div className="flex gap-2">
            <button className="border rounded px-3 py-2" onClick={onRegister}>Register</button>
            <button className="border rounded px-3 py-2" onClick={onLogin}>Login</button>
            <button className="border rounded px-3 py-2" onClick={onLogout}>Logout</button>
          </div>
          {authMsg && <p className="text-sm">{authMsg}</p>}
        </div>

        <div className="space-y-3 border rounded-xl p-4">
          <h2 className="font-semibold">Current Subscription</h2>
          {errMe ? <p className="text-red-500">{errMe}</p> : <pre className="text-xs overflow-auto">{JSON.stringify(me, null, 2)}</pre>}

          <h3 className="font-semibold">Dev Admin Key</h3>
          <input
            className="w-full border rounded p-2"
            value={devKey}
            onChange={(e) => setDevKey(e.target.value)}
          />
          <div className="flex gap-2 flex-wrap">
            <button className="border rounded px-3 py-2" onClick={() => onSetTier("observer")}>Set Observer</button>
            <button className="border rounded px-3 py-2" onClick={() => onSetTier("analyst")}>Set Analyst</button>
            <button className="border rounded px-3 py-2" onClick={() => onSetTier("pro")}>Set Pro</button>
          </div>
        </div>

        <div className="space-y-3 border rounded-xl p-4">
          <h2 className="font-semibold">Signals Preview</h2>
          <button className="border rounded px-3 py-2" onClick={refreshAll}>Refresh feed</button>
          {errFeed ? <p className="text-red-500">{errFeed}</p> : <pre className="text-xs overflow-auto">{JSON.stringify(feed, null, 2)}</pre>}
        </div>
      </section>

      <section className="border rounded-xl p-4">
        <h2 className="font-semibold mb-2">Available Plans</h2>
        {errPlans ? <p className="text-red-500">{errPlans}</p> : <pre className="text-xs overflow-auto">{JSON.stringify(plans, null, 2)}</pre>}
      </section>
    </main>
  );
}
