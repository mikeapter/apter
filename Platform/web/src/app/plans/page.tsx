"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchJson } from "../../lib/api";

type Plan = {
  tier: string;
  name: string;
  price_usd_month: number;
};

type PlansResponse = { plans?: Plan[] };

export default function PlansPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [tier, setTier] = useState("Observer");
  const [globalError, setGlobalError] = useState("");
  const [signalsWarning, setSignalsWarning] = useState("");
  const [loading, setLoading] = useState(true);

  const loadPage = useCallback(async () => {
    setLoading(true);
    setGlobalError("");
    setSignalsWarning("");

    try {
      const plansRes = await fetchJson<PlansResponse>("/api/plans");
      setPlans(plansRes.plans ?? []);

      // Optional tier endpoint
      try {
        const me = await fetchJson<{ tier?: string; name?: string }>("/api/subscription/me");
        setTier(me?.tier || me?.name || "Observer");
      } catch {
        setTier("Observer");
      }

      // Optional signals endpoint (your API currently returns 404 here)
      try {
        await fetchJson("/api/signals/feed?limit=5");
      } catch {
        setSignalsWarning("Signals feed endpoint not available yet.");
      }
    } catch (err: any) {
      setGlobalError(err?.message || "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPage();
  }, [loadPage]);

  return (
    <div className="p-6 text-white">
      <h1 className="text-4xl font-bold">Subscription Plans</h1>
      <p className="mt-3 text-slate-300">
        Signals-only trading tool. No auto-execution.
      </p>

      {loading && <p className="mt-4 text-slate-300">Loading…</p>}
      {globalError && <p className="mt-4 text-red-400">{globalError}</p>}
      {signalsWarning && <p className="mt-2 text-amber-300">{signalsWarning}</p>}

      <div className="mt-4 text-slate-200">Current tier: {tier}</div>

      <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        {plans.map((p) => (
          <div key={p.tier} className="rounded border border-slate-800 bg-[#0a1136] p-4">
            <div className="text-sm text-slate-400">{p.tier}</div>
            <div className="text-xl font-semibold">{p.name}</div>
            <div className="text-slate-200">${p.price_usd_month}/month</div>
          </div>
        ))}
      </div>
    </div>
  );
}
