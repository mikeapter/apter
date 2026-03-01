"use client";

import Link from "next/link";
import { Lock } from "lucide-react";
import { tierLabel } from "./FeatureGate";

type LockedPanelProps = {
  /** Minimum tier required: "signals" or "pro" */
  requiredTier: "signals" | "pro";
  /** Short title for the locked section */
  title?: string;
  /** 1-2 benefit bullets */
  benefits?: [string, string?];
};

/**
 * Locked-state panel shown to users below the required tier.
 * Displays a title, benefit bullets, and an upgrade button.
 */
export function LockedPanel({
  requiredTier,
  title,
  benefits,
}: LockedPanelProps) {
  const label = tierLabel(requiredTier);
  const heading = title ?? `Available on ${label}`;

  const defaultBenefits: [string, string?] =
    requiredTier === "pro"
      ? ["Extended historical data and analytics", "Signal strength and confidence bands"]
      : ["Full pillar breakdown and key drivers", "Bull/bear case narratives"];

  const bullets = benefits ?? defaultBenefits;

  return (
    <div className="rounded-md border border-border bg-panel-2/50 p-5 flex flex-col items-center text-center gap-3">
      <div className="w-9 h-9 rounded-full border border-border bg-muted flex items-center justify-center">
        <Lock size={16} className="text-muted-foreground" />
      </div>

      <div className="text-sm font-semibold">{heading}</div>

      <ul className="text-xs text-muted-foreground space-y-1">
        {bullets.filter(Boolean).map((b, i) => (
          <li key={i}>{b}</li>
        ))}
      </ul>

      <Link
        href="/plans"
        className="mt-1 inline-flex h-8 items-center rounded-md border border-risk-on/40 px-4 text-xs font-semibold text-risk-on hover:bg-risk-on/10 transition-colors"
      >
        Upgrade to {label}
      </Link>
    </div>
  );
}
