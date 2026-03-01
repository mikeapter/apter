import { tierLabel } from "./FeatureGate";

type TierBadgeProps = {
  /** The tier this panel requires: "signals" or "pro" */
  tier: "signals" | "pro";
};

/**
 * Subtle inline badge indicating a panel's required tier.
 * Uses a muted border and text — no bright colors.
 */
export function TierBadge({ tier }: TierBadgeProps) {
  return (
    <span className="inline-flex items-center rounded border border-border px-1.5 py-0.5 text-[9px] uppercase tracking-[0.14em] font-semibold text-muted-foreground leading-none">
      {tierLabel(tier)}
    </span>
  );
}
