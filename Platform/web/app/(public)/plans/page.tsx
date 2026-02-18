"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiGet, apiPost } from "@/lib/api";
import { getToken } from "@/lib/auth";

type PlanTier = "free" | "standard" | "pro";

type Plan = {
  tier: PlanTier;
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

type SubscriptionMeResponse = {
  tier: PlanTier;
  plan: Plan;
  status: string;
  updated_at: string;
};

export default function PlansPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-[60vh]"><div className="text-sm text-muted-foreground">Loading...</div></div>}>
      <PlansContent />
    </Suspense>
  );
}

function PlansContent() {
  const searchParams = useSearchParams();
  const success = searchParams?.get("success");
  const canceled = searchParams?.get("canceled");

  const [plans, setPlans] = useState<Plan[]>([]);
  const [plansError, setPlansError] = useState<string | null>(null);
  const [me, setMe] = useState<SubscriptionMeResponse | null>(null);
  const [upgradeLoading, setUpgradeLoading] = useState<string | null>(null);
  const [upgradeError, setUpgradeError] = useState<string | null>(null);

  const token = useMemo(() => {
    if (typeof window === "undefined") return null;
    return getToken();
  }, []);

  useEffect(() => {
    apiGet<{ plans: Plan[] }>("/api/plans").then((r) => {
      if (r.ok) setPlans(r.data.plans);
      else setPlansError(r.error);
    });
  }, []);

  useEffect(() => {
    if (!token) return;
    apiGet<SubscriptionMeResponse>("/api/subscription/me", undefined, token).then(
      (r) => {
        if (r.ok) setMe(r.data);
      }
    );
  }, [token]);

  const currentTier: PlanTier = me?.tier ?? "free";

  async function handleUpgrade(tier: PlanTier) {
    if (!token) return; // button should route to /register if no token
    setUpgradeError(null);
    setUpgradeLoading(tier);

    const r = await apiPost<{ checkout_url: string }>(
      "/api/stripe/create-checkout-session",
      { tier },
      undefined,
      token
    );

    setUpgradeLoading(null);

    if (!r.ok) {
      setUpgradeError(r.error);
      return;
    }

    window.location.href = r.data.checkout_url;
  }

  async function handleManage() {
    if (!token) return;
    const r = await apiPost<{ portal_url: string }>(
      "/api/stripe/create-portal-session",
      {},
      undefined,
      token
    );
    if (r.ok) {
      window.location.href = r.data.portal_url;
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-10 space-y-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Subscription Plans</h1>
        <p className="text-muted-foreground">
          Choose the analytics tier that fits your research needs. All tiers include the institutional-quality dashboard.
        </p>
      </div>

      {/* Success/cancel banners */}
      {success && (
        <div className="rounded-md border border-risk-on/40 bg-risk-on/5 p-4 text-sm text-risk-on">
          Subscription activated successfully. Your tier has been updated.
        </div>
      )}
      {canceled && (
        <div className="rounded-md border border-risk-neutral/40 bg-risk-neutral/5 p-4 text-sm text-risk-neutral">
          Checkout was canceled. No changes were made to your subscription.
        </div>
      )}

      {/* Current subscription (logged in only) */}
      {token && me && (
        <div className="bt-panel p-4 flex items-center justify-between">
          <div className="text-sm">
            Current tier:{" "}
            <span className="font-semibold">{me.tier.toUpperCase()}</span>
            {" \u00b7 "}
            Status: <span className="font-semibold">{me.status}</span>
          </div>
          {me.tier !== "free" && (
            <button
              onClick={handleManage}
              className="bt-button hover:bg-muted text-sm"
            >
              Manage Subscription
            </button>
          )}
        </div>
      )}

      {upgradeError && (
        <div className="text-sm text-red-400">{upgradeError}</div>
      )}

      {/* Plan cards */}
      <div className="grid gap-4 lg:grid-cols-3">
        {plansError ? (
          <div className="text-red-400">{plansError}</div>
        ) : (
          plans.map((p) => (
            <PlanCard
              key={p.tier}
              plan={p}
              isCurrent={p.tier === currentTier}
              isLoggedIn={!!token}
              loading={upgradeLoading === p.tier}
              onUpgrade={() => handleUpgrade(p.tier)}
            />
          ))
        )}
      </div>
    </div>
  );
}

function PlanCard({
  plan,
  isCurrent,
  isLoggedIn,
  loading,
  onUpgrade,
}: {
  plan: Plan;
  isCurrent: boolean;
  isLoggedIn: boolean;
  loading: boolean;
  onUpgrade: () => void;
}) {
  const price =
    plan.price_usd_month === 0 ? "Free" : `$${plan.price_usd_month}/mo`;

  function buttonContent() {
    if (isCurrent) return "Current Plan";
    if (plan.price_usd_month === 0) return "Free Tier";
    if (!isLoggedIn) return "Sign Up to Upgrade";
    if (loading) return "Redirecting...";
    return `Upgrade to ${plan.name}`;
  }

  function handleClick() {
    if (isCurrent || plan.price_usd_month === 0) return;
    if (!isLoggedIn) {
      window.location.href = `/register?next=/plans`;
      return;
    }
    onUpgrade();
  }

  return (
    <div className="rounded-lg border border-border bg-card p-5 flex flex-col">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xl font-semibold">{plan.name}</div>
          <div className="text-muted-foreground text-sm mt-1">
            {plan.target_user}
          </div>
        </div>
        <div className="text-lg font-bold">{price}</div>
      </div>

      <div className="mt-4">
        <div className="text-sm font-semibold mb-2">Included</div>
        <ul className="text-sm text-muted-foreground space-y-1 list-disc pl-5">
          {plan.features.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      </div>

      <div className="mt-4">
        <div className="text-sm font-semibold mb-2">Excluded</div>
        <ul className="text-sm text-muted-foreground space-y-1 list-disc pl-5">
          {plan.exclusions.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      </div>

      <div className="mt-4 text-xs text-muted-foreground">
        Limits: delay {plan.limits.signal_delay_seconds}s &middot; max{" "}
        {plan.limits.max_signals_per_response} signals &middot; history{" "}
        {plan.limits.history_days} days
      </div>

      <div className="mt-4 flex-1" />
      <button
        className={`h-11 rounded-md border text-sm font-semibold ${
          isCurrent || plan.price_usd_month === 0
            ? "border-border opacity-60 cursor-default"
            : "border-risk-on/40 text-risk-on hover:bg-risk-on/10"
        }`}
        onClick={handleClick}
        disabled={isCurrent || loading || plan.price_usd_month === 0}
      >
        {buttonContent()}
      </button>
    </div>
  );
}
