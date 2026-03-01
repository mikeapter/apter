"use client";

import { useAuth } from "../../hooks/useAuth";
import { LockedPanel } from "./LockedPanel";

/**
 * Backend tier values mapped to numeric rank for comparison.
 * Backend returns: observer (free), signals (mid), pro (top).
 */
const TIER_RANK: Record<string, number> = {
  observer: 0,
  free: 0,
  signals: 1,
  standard: 1,
  pro: 2,
};

function tierMeetsMin(current: string, required: string): boolean {
  return (TIER_RANK[current] ?? 0) >= (TIER_RANK[required] ?? 0);
}

/** Human-readable label for the required tier. */
export function tierLabel(tier: string): string {
  if (tier === "signals" || tier === "standard") return "Signals";
  if (tier === "pro") return "Pro";
  return "Free";
}

type FeatureGateProps = {
  /** Minimum tier required: "signals" or "pro" */
  requiredTier: "signals" | "pro";
  /** Short title shown on the locked panel */
  title?: string;
  /** 1-2 benefit bullets shown on the locked panel */
  benefits?: [string, string?];
  children: React.ReactNode;
};

/**
 * Wraps content behind a tier gate.
 * Renders children if the user's tier meets the minimum,
 * otherwise shows a LockedPanel with upgrade CTA.
 */
export function FeatureGate({
  requiredTier,
  title,
  benefits,
  children,
}: FeatureGateProps) {
  const { user, loading } = useAuth();

  if (loading) return null;

  const userTier = user?.tier ?? "observer";

  if (tierMeetsMin(userTier, requiredTier)) {
    return <>{children}</>;
  }

  return (
    <LockedPanel
      requiredTier={requiredTier}
      title={title}
      benefits={benefits}
    />
  );
}
