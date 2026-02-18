export type PlanTier = "free" | "standard" | "pro";

const TIER_RANK: Record<string, number> = {
  free: 0,
  standard: 1,
  pro: 2,
};

export function tierAtLeast(current: string, required: string): boolean {
  return (TIER_RANK[current] ?? 0) >= (TIER_RANK[required] ?? 0);
}
