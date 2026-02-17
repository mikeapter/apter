export type StockDetail = {
  ticker: string;
  companyName: string;
  sector: string;
  price: number;
  change: number;
  changePct: number;
  grade: number;
  gradeBreakdown: GradeBreakdown;
  aiOverview: string;
  newsItems: NewsItem[];
  decisionSupport: DecisionSupportData;
};

export type GradeBreakdown = {
  momentum: number;
  valuation: number;
  quality: number;
  volatility: number;
  sentiment: number;
};

export type NewsItem = {
  headline: string;
  source: string;
  timestamp: string;
  sentiment: "positive" | "neutral" | "negative";
};

export type DecisionSupportData = {
  momentum: { label: string; value: string; description: string };
  volatility: { label: string; value: string; description: string };
  earnings: { label: string; value: string; description: string };
  valuation: { label: string; value: string; description: string };
  peerComparison: { label: string; value: string; description: string };
};

const STOCK_DB: Record<string, StockDetail> = {
  AAPL: {
    ticker: "AAPL",
    companyName: "Apple Inc.",
    sector: "Technology",
    price: 234.56,
    change: 3.21,
    changePct: 1.39,
    grade: 7,
    gradeBreakdown: { momentum: 7, valuation: 5, quality: 9, volatility: 8, sentiment: 6 },
    aiOverview: "Apple shows stable revenue growth with consistent free cash flow generation. Services segment continues to expand as a share of total revenue. Hardware cycle timing remains a key variable for near-term performance. Institutional ownership remains high with moderate short interest.",
    newsItems: [
      { headline: "Apple expands services revenue to record quarter", source: "Financial Times", timestamp: "2026-02-16 09:15", sentiment: "positive" },
      { headline: "iPhone supply chain signals stable production outlook", source: "Reuters", timestamp: "2026-02-15 14:30", sentiment: "neutral" },
      { headline: "Apple AI features drive upgrade cycle expectations", source: "Bloomberg", timestamp: "2026-02-14 11:00", sentiment: "positive" },
    ],
    decisionSupport: {
      momentum: { label: "Momentum", value: "Moderate Positive", description: "Price is above 50-day and 200-day moving averages. RSI at 58 indicates neutral-to-positive momentum." },
      volatility: { label: "Volatility Regime", value: "Low", description: "30-day realized volatility at 18.2%, below sector median. Implied volatility term structure is flat." },
      earnings: { label: "Earnings Context", value: "Beat Consensus +4.2%", description: "Most recent quarter exceeded consensus EPS by 4.2%. Revenue in-line. Next report estimated in 6 weeks." },
      valuation: { label: "Valuation Snapshot", value: "P/E 29.3x", description: "Forward P/E of 29.3x, above 5-year median of 26.1x. PEG ratio of 2.1x suggests growth-adjusted premium." },
      peerComparison: { label: "Peer Comparison", value: "Above Median", description: "Outperforming mega-cap tech peers on 3-month basis. Relative strength vs. QQQ is positive." },
    },
  },
  MSFT: {
    ticker: "MSFT",
    companyName: "Microsoft Corporation",
    sector: "Technology",
    price: 428.90,
    change: 5.67,
    changePct: 1.34,
    grade: 8,
    gradeBreakdown: { momentum: 8, valuation: 6, quality: 9, volatility: 7, sentiment: 8 },
    aiOverview: "Microsoft maintains strong growth driven by Azure cloud services and AI integration across its product suite. Enterprise spending on cloud infrastructure continues to accelerate. Operating margins remain above sector average with consistent capital return via buybacks and dividends.",
    newsItems: [
      { headline: "Azure revenue growth accelerates to 32% year-over-year", source: "Bloomberg", timestamp: "2026-02-16 10:00", sentiment: "positive" },
      { headline: "Microsoft AI Copilot adoption reaches enterprise milestone", source: "CNBC", timestamp: "2026-02-15 08:45", sentiment: "positive" },
      { headline: "Cloud infrastructure competition intensifies across hyperscalers", source: "WSJ", timestamp: "2026-02-13 16:20", sentiment: "neutral" },
    ],
    decisionSupport: {
      momentum: { label: "Momentum", value: "Strong Positive", description: "Consistent higher highs and higher lows. RSI at 64 with positive MACD crossover." },
      volatility: { label: "Volatility Regime", value: "Below Average", description: "30-day realized volatility at 16.5%. Options skew is minimal." },
      earnings: { label: "Earnings Context", value: "Beat Consensus +6.1%", description: "Strong beat on cloud revenue. Guidance raised for full fiscal year." },
      valuation: { label: "Valuation Snapshot", value: "P/E 34.2x", description: "Forward P/E of 34.2x. Premium justified by AI growth optionality per consensus." },
      peerComparison: { label: "Peer Comparison", value: "Top Quartile", description: "Leading mega-cap tech on cloud growth metrics. Highest operating margin in peer group." },
    },
  },
  NVDA: {
    ticker: "NVDA",
    companyName: "NVIDIA Corporation",
    sector: "Technology",
    price: 876.32,
    change: -12.45,
    changePct: -1.40,
    grade: 6,
    gradeBreakdown: { momentum: 5, valuation: 3, quality: 8, volatility: 4, sentiment: 7 },
    aiOverview: "NVIDIA remains the dominant GPU supplier for AI training and inference workloads. Revenue growth has been exceptional but valuation multiples reflect high expectations. Supply constraints are easing while competition from custom silicon is emerging. Concentration risk in data center segment is notable.",
    newsItems: [
      { headline: "NVIDIA data center revenue exceeds estimates but guidance mixed", source: "Reuters", timestamp: "2026-02-16 11:30", sentiment: "neutral" },
      { headline: "Custom AI chip development accelerates at major cloud providers", source: "The Information", timestamp: "2026-02-15 09:00", sentiment: "negative" },
      { headline: "Blackwell architecture shipping at scale to hyperscalers", source: "Bloomberg", timestamp: "2026-02-14 14:00", sentiment: "positive" },
    ],
    decisionSupport: {
      momentum: { label: "Momentum", value: "Neutral", description: "Price consolidating after extended run. RSI at 48, near oversold levels for this stock's range." },
      volatility: { label: "Volatility Regime", value: "Elevated", description: "30-day realized volatility at 42.1%, well above sector median. Implied vol skew is negative." },
      earnings: { label: "Earnings Context", value: "Beat +8.3% (mixed guidance)", description: "Beat on revenue and EPS but forward guidance range wider than typical." },
      valuation: { label: "Valuation Snapshot", value: "P/E 48.7x", description: "Forward P/E of 48.7x. PEG ratio of 1.3x given high growth rate." },
      peerComparison: { label: "Peer Comparison", value: "Premium to Peers", description: "Highest valuation multiple in semiconductor peer group. Highest revenue growth rate." },
    },
  },
  GOOGL: {
    ticker: "GOOGL",
    companyName: "Alphabet Inc.",
    sector: "Technology",
    price: 178.45,
    change: 1.23,
    changePct: 0.69,
    grade: 7,
    gradeBreakdown: { momentum: 6, valuation: 7, quality: 8, volatility: 7, sentiment: 6 },
    aiOverview: "Alphabet demonstrates broad revenue diversification across Search, Cloud, and YouTube. Google Cloud growth is accelerating with improving margins. Search revenue remains resilient despite competitive AI search developments. Capital expenditure is elevated for AI infrastructure build-out.",
    newsItems: [
      { headline: "Google Cloud profitability improves for third consecutive quarter", source: "CNBC", timestamp: "2026-02-16 08:30", sentiment: "positive" },
      { headline: "Search advertising market share holds steady amid AI disruption", source: "WSJ", timestamp: "2026-02-14 10:15", sentiment: "neutral" },
    ],
    decisionSupport: {
      momentum: { label: "Momentum", value: "Moderate Positive", description: "Above key moving averages. RSI at 55." },
      volatility: { label: "Volatility Regime", value: "Normal", description: "30-day realized vol at 22.4%, in line with historical median." },
      earnings: { label: "Earnings Context", value: "Beat Consensus +3.8%", description: "Cloud segment drove the beat. Advertising revenue in line." },
      valuation: { label: "Valuation Snapshot", value: "P/E 22.8x", description: "Attractive relative to mega-cap peers. Below 5-year median P/E." },
      peerComparison: { label: "Peer Comparison", value: "Median", description: "Mid-pack on growth, favorable on valuation vs. mega-cap tech." },
    },
  },
  AMZN: {
    ticker: "AMZN",
    companyName: "Amazon.com Inc.",
    sector: "Consumer Discretionary",
    price: 212.78,
    change: 4.56,
    changePct: 2.19,
    grade: 7,
    gradeBreakdown: { momentum: 7, valuation: 5, quality: 7, volatility: 6, sentiment: 8 },
    aiOverview: "Amazon continues margin expansion in both AWS and retail segments. AWS maintains market leadership in cloud infrastructure. E-commerce profitability has improved meaningfully through operational efficiency initiatives. Advertising business is a high-margin growth contributor.",
    newsItems: [
      { headline: "AWS maintains cloud market share leadership at 32%", source: "Gartner", timestamp: "2026-02-15 12:00", sentiment: "positive" },
      { headline: "Amazon retail margins hit record levels on efficiency gains", source: "Bloomberg", timestamp: "2026-02-14 15:30", sentiment: "positive" },
    ],
    decisionSupport: {
      momentum: { label: "Momentum", value: "Positive", description: "Strong trend with RSI at 61. MACD positive." },
      volatility: { label: "Volatility Regime", value: "Moderate", description: "30-day realized vol at 26.8%." },
      earnings: { label: "Earnings Context", value: "Beat Consensus +5.4%", description: "Broad-based beat. AWS growth re-accelerated." },
      valuation: { label: "Valuation Snapshot", value: "P/E 38.1x", description: "Forward P/E of 38.1x, above historical median." },
      peerComparison: { label: "Peer Comparison", value: "Above Median", description: "Leading on revenue growth among mega-caps." },
    },
  },
  META: {
    ticker: "META",
    companyName: "Meta Platforms Inc.",
    sector: "Technology",
    price: 612.34,
    change: 8.91,
    changePct: 1.48,
    grade: 7,
    gradeBreakdown: { momentum: 7, valuation: 6, quality: 8, volatility: 6, sentiment: 7 },
    aiOverview: "Meta demonstrates strong advertising revenue recovery with improving engagement metrics across its family of apps. AI-driven content recommendations are driving time-on-platform increases. Reality Labs segment continues to incur significant losses but management maintains long-term commitment.",
    newsItems: [
      { headline: "Meta advertising revenue growth exceeds industry average", source: "Financial Times", timestamp: "2026-02-15 11:00", sentiment: "positive" },
      { headline: "Instagram Reels engagement metrics show positive trajectory", source: "CNBC", timestamp: "2026-02-14 09:30", sentiment: "positive" },
    ],
    decisionSupport: {
      momentum: { label: "Momentum", value: "Positive", description: "RSI at 59. Trending above all major moving averages." },
      volatility: { label: "Volatility Regime", value: "Moderate", description: "30-day realized vol at 28.5%." },
      earnings: { label: "Earnings Context", value: "Beat Consensus +7.2%", description: "Strong advertising revenue. Capex guidance higher than expected." },
      valuation: { label: "Valuation Snapshot", value: "P/E 24.6x", description: "Reasonable relative to growth rate. Below sector median." },
      peerComparison: { label: "Peer Comparison", value: "Above Median", description: "Best operating margin improvement among mega-cap peers." },
    },
  },
  TSLA: {
    ticker: "TSLA",
    companyName: "Tesla Inc.",
    sector: "Consumer Discretionary",
    price: 342.18,
    change: -8.76,
    changePct: -2.49,
    grade: 4,
    gradeBreakdown: { momentum: 4, valuation: 2, quality: 5, volatility: 3, sentiment: 5 },
    aiOverview: "Tesla faces intensifying competition in the global EV market with margin pressure from pricing adjustments. Energy storage and autonomous driving segments represent potential growth vectors but timelines remain uncertain. Delivery volume growth has decelerated relative to prior years.",
    newsItems: [
      { headline: "EV competition intensifies as legacy automakers scale production", source: "Reuters", timestamp: "2026-02-16 13:00", sentiment: "negative" },
      { headline: "Tesla energy storage deployments hit quarterly record", source: "Bloomberg", timestamp: "2026-02-15 10:15", sentiment: "positive" },
    ],
    decisionSupport: {
      momentum: { label: "Momentum", value: "Weak Negative", description: "Below 50-day MA. RSI at 42." },
      volatility: { label: "Volatility Regime", value: "High", description: "30-day realized vol at 52.3%, among highest in large-cap universe." },
      earnings: { label: "Earnings Context", value: "Missed Consensus -2.1%", description: "Margin compression on pricing actions. Delivery guidance maintained." },
      valuation: { label: "Valuation Snapshot", value: "P/E 68.4x", description: "Premium valuation reflecting growth and optionality assumptions." },
      peerComparison: { label: "Peer Comparison", value: "Premium", description: "Highest valuation in auto sector. Unique positioning between tech and auto." },
    },
  },
  SPY: {
    ticker: "SPY",
    companyName: "SPDR S&P 500 ETF Trust",
    sector: "Broad Market ETF",
    price: 512.34,
    change: 2.45,
    changePct: 0.48,
    grade: 6,
    gradeBreakdown: { momentum: 6, valuation: 5, quality: 7, volatility: 7, sentiment: 6 },
    aiOverview: "SPY tracks the S&P 500 index, providing broad large-cap U.S. equity exposure. Current market conditions show moderate breadth with leadership concentrated in technology. Earnings growth expectations for the index are positive but decelerating. Sector rotation dynamics remain a key theme.",
    newsItems: [
      { headline: "S&P 500 breadth improves as mid-caps participate in rally", source: "MarketWatch", timestamp: "2026-02-16 09:45", sentiment: "positive" },
      { headline: "Forward earnings estimates for S&P 500 revised modestly higher", source: "FactSet", timestamp: "2026-02-14 08:00", sentiment: "positive" },
    ],
    decisionSupport: {
      momentum: { label: "Momentum", value: "Moderate Positive", description: "Index above 50 and 200-day MAs. RSI at 56." },
      volatility: { label: "Volatility Regime", value: "Normal", description: "VIX at 16.2, below long-term average." },
      earnings: { label: "Earnings Context", value: "Blended Growth +8.2%", description: "S&P 500 earnings growing at 8.2% year-over-year on blended basis." },
      valuation: { label: "Valuation Snapshot", value: "P/E 21.4x", description: "Forward P/E of 21.4x, above historical average of 17.5x." },
      peerComparison: { label: "Peer Comparison", value: "N/A (Index)", description: "Benchmark index. Compare vs. international and small-cap alternatives." },
    },
  },
  QQQ: {
    ticker: "QQQ",
    companyName: "Invesco QQQ Trust",
    sector: "Technology ETF",
    price: 438.67,
    change: 3.12,
    changePct: 0.72,
    grade: 6,
    gradeBreakdown: { momentum: 6, valuation: 4, quality: 8, volatility: 6, sentiment: 6 },
    aiOverview: "QQQ tracks the Nasdaq-100 index with heavy concentration in mega-cap technology. The index benefits from AI-driven growth but carries elevated valuation risk. Top holdings represent significant concentration. Tech sector fundamentals remain strong but expectations are high.",
    newsItems: [
      { headline: "Nasdaq-100 concentration in top 5 holdings reaches 40%", source: "S&P Global", timestamp: "2026-02-15 14:00", sentiment: "neutral" },
    ],
    decisionSupport: {
      momentum: { label: "Momentum", value: "Moderate Positive", description: "RSI at 57. Above major moving averages." },
      volatility: { label: "Volatility Regime", value: "Moderate", description: "Higher beta than SPY. 30-day vol at 21.3%." },
      earnings: { label: "Earnings Context", value: "Blended Growth +12.4%", description: "Tech-heavy composition driving above-average earnings growth." },
      valuation: { label: "Valuation Snapshot", value: "P/E 28.7x", description: "Premium to S&P 500, reflecting growth expectations." },
      peerComparison: { label: "Peer Comparison", value: "N/A (Index)", description: "Growth-oriented benchmark. Higher risk/return profile than SPY." },
    },
  },
  JPM: {
    ticker: "JPM",
    companyName: "JPMorgan Chase & Co.",
    sector: "Financials",
    price: 198.45,
    change: 1.89,
    changePct: 0.96,
    grade: 7,
    gradeBreakdown: { momentum: 7, valuation: 7, quality: 8, volatility: 8, sentiment: 6 },
    aiOverview: "JPMorgan maintains its position as the largest U.S. bank by assets with diversified revenue streams across investment banking, consumer banking, and asset management. Net interest income benefits from the current rate environment. Credit quality metrics remain strong with manageable reserve levels.",
    newsItems: [
      { headline: "JPMorgan investment banking fees rise on improved deal activity", source: "Financial Times", timestamp: "2026-02-15 16:00", sentiment: "positive" },
      { headline: "Consumer credit quality remains stable across major banks", source: "FDIC", timestamp: "2026-02-14 12:00", sentiment: "neutral" },
    ],
    decisionSupport: {
      momentum: { label: "Momentum", value: "Positive", description: "Trending higher. RSI at 60. Financial sector rotation favorable." },
      volatility: { label: "Volatility Regime", value: "Low", description: "30-day realized vol at 14.8%. Defensive characteristics." },
      earnings: { label: "Earnings Context", value: "Beat Consensus +3.1%", description: "Investment banking recovery and stable NII drove beat." },
      valuation: { label: "Valuation Snapshot", value: "P/E 12.1x", description: "Attractive absolute valuation. Premium to bank peers justified by quality." },
      peerComparison: { label: "Peer Comparison", value: "Top of Class", description: "Highest ROE among large-cap banks. Best-in-class efficiency ratio." },
    },
  },
};

/** Get stock detail for a ticker. Falls back to a generic entry for unknown tickers. */
export function getStockDetail(ticker: string): StockDetail {
  const upper = ticker.toUpperCase().trim();
  if (STOCK_DB[upper]) return STOCK_DB[upper];

  return {
    ticker: upper,
    companyName: `${upper} (Data Pending)`,
    sector: "Unknown",
    price: 0,
    change: 0,
    changePct: 0,
    grade: 5,
    gradeBreakdown: { momentum: 5, valuation: 5, quality: 5, volatility: 5, sentiment: 5 },
    aiOverview: `Detailed analytics for ${upper} are not yet available in the sample dataset. In production, this section would display AI-generated factual performance analysis and key metrics.`,
    newsItems: [],
    decisionSupport: {
      momentum: { label: "Momentum", value: "N/A", description: "Data not available for this ticker in the sample dataset." },
      volatility: { label: "Volatility Regime", value: "N/A", description: "Data not available for this ticker in the sample dataset." },
      earnings: { label: "Earnings Context", value: "N/A", description: "Data not available for this ticker in the sample dataset." },
      valuation: { label: "Valuation Snapshot", value: "N/A", description: "Data not available for this ticker in the sample dataset." },
      peerComparison: { label: "Peer Comparison", value: "N/A", description: "Data not available for this ticker in the sample dataset." },
    },
  };
}

/** Get a mock current price for a ticker (used by portfolio valuation). */
export function getMockPrice(ticker: string): number {
  const upper = ticker.toUpperCase().trim();
  const stock = STOCK_DB[upper];
  if (stock) return stock.price;
  // Return a pseudo-random but stable price for unknown tickers
  let hash = 0;
  for (let i = 0; i < upper.length; i++) hash = ((hash << 5) - hash + upper.charCodeAt(i)) | 0;
  return 50 + Math.abs(hash % 300);
}

/** Get a mock grade for a ticker. */
export function getMockGrade(ticker: string): number {
  const upper = ticker.toUpperCase().trim();
  const stock = STOCK_DB[upper];
  if (stock) return stock.grade;
  let hash = 0;
  for (let i = 0; i < upper.length; i++) hash = ((hash << 5) - hash + upper.charCodeAt(i)) | 0;
  return 1 + Math.abs(hash % 10);
}

/** Generate sample chart data for a stock. */
export function generateStockChartData(ticker: string, range: string): Array<{ date: string; price: number }> {
  const basePrice = getMockPrice(ticker);
  const points: Array<{ date: string; price: number }> = [];

  let numPoints: number;
  switch (range) {
    case "1D": numPoints = 78; break;
    case "1W": numPoints = 5; break;
    case "1M": numPoints = 22; break;
    case "3M": numPoints = 65; break;
    case "1Y": numPoints = 252; break;
    case "ALL": numPoints = 504; break;
    default: numPoints = 22;
  }

  const baseDate = new Date("2026-02-16");
  let price = basePrice * 0.92;

  for (let i = numPoints; i >= 0; i--) {
    const d = new Date(baseDate);
    if (range === "1D") {
      d.setMinutes(d.getMinutes() - i * 5);
    } else {
      d.setDate(d.getDate() - i);
    }
    price += price * (Math.random() * 0.025 - 0.01);
    points.push({
      date: range === "1D"
        ? d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })
        : d.toISOString().slice(0, 10),
      price: parseFloat(price.toFixed(2)),
    });
  }

  return points;
}
