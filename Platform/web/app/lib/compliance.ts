/**
 * Central compliance disclosure strings.
 * All user-facing disclaimers must reference these constants
 * to ensure consistency across the authenticated app.
 */

export const COMPLIANCE = {
  GLOBAL_FOOTER:
    "Apter Financial provides analytics tools for informational and educational purposes only. Nothing on this platform is investment advice.",

  ASSISTANT_DISCLAIMER:
    "Apter Assistant provides data-driven analysis, not personalized investment advice.",

  BACKTEST_DISCLAIMER:
    "Backtested performance is hypothetical, has limitations, and does not guarantee future results.",

  PORTFOLIO_DISCLAIMER:
    "Risk metrics are analytical indicators and should not be interpreted as trade instructions.",

  GRADE_TOOLTIP:
    "Model score is not a buy/sell recommendation.",

  NOT_INVESTMENT_ADVICE:
    "For informational/educational use only. Not investment advice. No guarantee of future results.",

  DISCLOSURE_BANNER:
    "Information is for educational and research purposes only. Not investment advice. Apter Financial is not acting as a registered investment adviser.",
} as const;
