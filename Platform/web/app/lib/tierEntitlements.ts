export type PlanTier = "free" | "standard" | "pro";

export type Feature =
  | "screener_basic"
  | "screener_advanced"
  | "watchlist"
  | "cost_basis"
  | "earnings_calendar"
  | "basic_grade"
  | "ai_summary_short"
  | "risk_engine"
  | "portfolio_risk"
  | "insider_activity"
  | "earnings_probability"
  | "news_impact"
  | "backtests"
  | "regime_detection"
  | "factor_exposure"
  | "beta_risk"
  | "event_volatility"
  | "ai_10k_summary"
  | "sector_rotation"
  | "allocation_scenarios";

const TIER_FEATURES: Record<PlanTier, Set<Feature>> = {
  free: new Set<Feature>([
    "screener_basic",
    "watchlist",
    "cost_basis",
    "earnings_calendar",
    "basic_grade",
    "ai_summary_short",
  ]),
  standard: new Set<Feature>([
    // Includes all free features
    "screener_basic",
    "watchlist",
    "cost_basis",
    "earnings_calendar",
    "basic_grade",
    "ai_summary_short",
    // Standard additions
    "screener_advanced",
    "risk_engine",
    "portfolio_risk",
    "insider_activity",
    "earnings_probability",
    "news_impact",
    "backtests",
  ]),
  pro: new Set<Feature>([
    // Includes all standard features
    "screener_basic",
    "watchlist",
    "cost_basis",
    "earnings_calendar",
    "basic_grade",
    "ai_summary_short",
    "screener_advanced",
    "risk_engine",
    "portfolio_risk",
    "insider_activity",
    "earnings_probability",
    "news_impact",
    "backtests",
    // Pro additions
    "regime_detection",
    "factor_exposure",
    "beta_risk",
    "event_volatility",
    "ai_10k_summary",
    "sector_rotation",
    "allocation_scenarios",
  ]),
};

/** Check if a tier has access to a specific feature. */
export function hasTierAccess(tier: PlanTier, feature: Feature): boolean {
  return TIER_FEATURES[tier]?.has(feature) ?? false;
}

/** Numeric tier level for comparison (free=0, standard=1, pro=2). */
export function tierLevel(tier: PlanTier): number {
  if (tier === "pro") return 2;
  if (tier === "standard") return 1;
  return 0;
}

/** Check if user tier meets minimum required tier. */
export function meetsMinTier(userTier: PlanTier, requiredTier: PlanTier): boolean {
  return tierLevel(userTier) >= tierLevel(requiredTier);
}
