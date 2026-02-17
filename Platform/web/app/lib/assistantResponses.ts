export type AssistantResponse = {
  dataShows: string;
  whyItMatters: string;
  reviewNext: string[];
};

type PatternEntry = {
  keywords: string[];
  response: AssistantResponse;
};

const PATTERNS: PatternEntry[] = [
  {
    keywords: ["market", "overview", "today", "how is"],
    response: {
      dataShows: "Current market conditions show the S&P 500 trading near recent highs with moderate breadth. Volatility (VIX) is at 16.2, below the long-term average. Sector rotation favors technology and financials on a relative basis.",
      whyItMatters: "Low volatility environments historically support risk assets but can precede volatility expansions. Breadth divergence may signal concentration risk in index returns.",
      reviewNext: [
        "Check sector performance heat map for rotation signals",
        "Review portfolio concentration relative to index weights",
        "Monitor VIX term structure for volatility regime changes",
      ],
    },
  },
  {
    keywords: ["aapl", "apple"],
    response: {
      dataShows: "Apple (AAPL) is trading at $234.56, up 1.39% today. The stock carries a proprietary grade of 7/10. Momentum indicators show moderate positive bias with RSI at 58. Services revenue continues to grow as a share of total revenue.",
      whyItMatters: "Stable cash flow generation and services growth support the investment thesis. Hardware cycle timing and AI feature adoption are key variables for near-term performance assessment.",
      reviewNext: [
        "Review full grade breakdown for factor analysis",
        "Check earnings calendar for next reporting date",
        "Compare valuation metrics to mega-cap tech peers",
      ],
    },
  },
  {
    keywords: ["msft", "microsoft"],
    response: {
      dataShows: "Microsoft (MSFT) trades at $428.90 (+1.34%). Grade: 8/10. Azure cloud revenue growth accelerated to 32% year-over-year. Operating margins remain above sector average.",
      whyItMatters: "Cloud infrastructure demand is a secular growth driver. AI integration across the product suite creates multiple revenue expansion vectors.",
      reviewNext: [
        "Analyze Azure growth trajectory vs. AWS and Google Cloud",
        "Review capital expenditure trends for AI infrastructure",
        "Check institutional ownership changes",
      ],
    },
  },
  {
    keywords: ["nvda", "nvidia"],
    response: {
      dataShows: "NVIDIA (NVDA) is at $876.32, down 1.40% today. Grade: 6/10. The stock shows elevated volatility at 42.1% realized vol. Valuation at 48.7x forward P/E reflects high growth expectations.",
      whyItMatters: "GPU demand for AI training remains strong but competition from custom silicon is emerging. The wide valuation premium requires sustained execution on growth targets.",
      reviewNext: [
        "Review volatility regime in context of position sizing",
        "Check custom chip development timelines at major cloud providers",
        "Analyze earnings guidance range relative to consensus",
      ],
    },
  },
  {
    keywords: ["portfolio", "holdings", "positions"],
    response: {
      dataShows: "Your portfolio analytics are available in the Portfolio panel. Key metrics include position-level P/L, cost basis tracking, and proprietary grade scores for each holding.",
      whyItMatters: "Regular portfolio review helps identify concentration risks, assess position sizing relative to conviction, and track cost basis for performance measurement.",
      reviewNext: [
        "Review position weights for concentration risk",
        "Check which holdings have grade scores below 5",
        "Compare portfolio sector exposure to benchmark",
      ],
    },
  },
  {
    keywords: ["risk", "volatility", "drawdown"],
    response: {
      dataShows: "Market volatility as measured by the VIX is currently at 16.2, below the long-term average of 20. Cross-asset correlations are moderate. The 30-day realized volatility for the S&P 500 is 12.8%.",
      whyItMatters: "Volatility regime assessment informs position sizing and risk budgeting decisions. Low-volatility environments can transition quickly, making preparation important.",
      reviewNext: [
        "Review portfolio-level volatility exposure",
        "Check correlation between largest holdings",
        "Assess drawdown scenarios under volatility expansion",
      ],
    },
  },
  {
    keywords: ["sector", "rotation", "performance"],
    response: {
      dataShows: "Current sector leadership: Technology (+2.1% MTD), Financials (+1.8% MTD), Healthcare (+0.9% MTD). Lagging: Energy (-1.2% MTD), Utilities (-0.8% MTD), Materials (-0.5% MTD).",
      whyItMatters: "Sector rotation patterns can indicate changes in economic growth expectations and risk appetite. Divergence between cyclical and defensive sectors provides macro context.",
      reviewNext: [
        "Compare portfolio sector weights to leadership trends",
        "Review individual sector ETFs for trend confirmation",
        "Check economic data releases that may drive rotation",
      ],
    },
  },
  {
    keywords: ["earnings", "report", "quarter"],
    response: {
      dataShows: "S&P 500 blended earnings growth is +8.2% year-over-year. Of companies reporting so far, 76% have beaten EPS estimates. Forward estimates have been revised modestly higher.",
      whyItMatters: "Earnings growth trajectory and estimate revisions are key drivers of equity returns. Beat rates above historical averages suggest reasonable analyst expectations.",
      reviewNext: [
        "Check earnings calendar for holdings approaching report dates",
        "Review historical earnings reactions for key positions",
        "Assess estimate revision trends for watchlist stocks",
      ],
    },
  },
  {
    keywords: ["grade", "score", "rating"],
    response: {
      dataShows: "The proprietary grade system scores securities on a 1-10 scale using multiple factor inputs: momentum, valuation, quality, volatility, and sentiment. Each factor contributes to the composite score.",
      whyItMatters: "Multi-factor scoring provides a systematic framework for comparing securities across dimensions. No single factor should be used in isolation for decision-making.",
      reviewNext: [
        "Review grade breakdown for specific holdings",
        "Compare grades across holdings to identify relative positioning",
        "Check which factor is driving the highest and lowest scores",
      ],
    },
  },
  {
    keywords: ["screener", "filter", "find"],
    response: {
      dataShows: "The screener tool allows filtering the investable universe by market cap, sector, grade range, and other quantitative criteria. Results are sorted by proprietary grade by default.",
      whyItMatters: "Systematic screening reduces cognitive bias in opportunity identification. Combining multiple filters narrows the universe to securities matching specific analytical criteria.",
      reviewNext: [
        "Start with broad filters and narrow progressively",
        "Use grade thresholds to focus on higher-scored securities",
        "Compare screener results with current portfolio gaps",
      ],
    },
  },
];

const FALLBACK_RESPONSE: AssistantResponse = {
  dataShows: "I can help with market analysis, stock data, portfolio analytics, and platform feature questions. Try asking about a specific ticker, market conditions, or your portfolio.",
  whyItMatters: "Focused questions help me provide more relevant analytical context and data points.",
  reviewNext: [
    "Ask about a specific stock (e.g., 'Tell me about AAPL')",
    "Ask about market conditions (e.g., 'How is the market today?')",
    "Ask about your portfolio (e.g., 'Review my portfolio')",
  ],
};

/** Match user input against known patterns and return a structured response. */
export function getAssistantResponse(input: string): AssistantResponse {
  const lower = input.toLowerCase().trim();
  if (!lower) return FALLBACK_RESPONSE;

  for (const pattern of PATTERNS) {
    if (pattern.keywords.some((kw) => lower.includes(kw))) {
      return pattern.response;
    }
  }

  return FALLBACK_RESPONSE;
}
