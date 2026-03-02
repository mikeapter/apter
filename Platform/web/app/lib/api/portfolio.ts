/**
 * Portfolio analytics API client.
 *
 * Talks to:
 *   POST /api/portfolio/summary
 *   POST /api/portfolio/ai-brief
 */

// ─── Types ───────────────────────────────────────────────────────────────────

export type HoldingInput = {
  ticker: string;
  shares: number;
  purchasePrice: number;
};

export type EnrichedHoldingSummary = {
  ticker: string;
  name: string;
  sector: string;
  shares: number;
  avgCost: number;
  price: number;
  marketValue: number;
  costBasis: number;
  unrealizedPL: number;
  unrealizedPLPct: number;
  dayPL: number;
  weightPct: number;
};

export type SectorAllocation = {
  sector: string;
  marketValue: number;
  weightPct: number;
};

export type Contributor = {
  ticker: string;
  contributionPct: number;
  pl: number;
};

export type PortfolioSummary = {
  range: string;
  asOf: string;
  totals: {
    marketValue: number;
    costBasis: number;
    unrealizedPL: number;
    unrealizedPLPct: number;
    dayPL: number;
    dayPLPct: number;
  };
  holdings: EnrichedHoldingSummary[];
  sectorAllocations: SectorAllocation[];
  contributors: {
    topGainers: Contributor[];
    topLosers: Contributor[];
  };
  concentration: {
    topHoldingWeightPct: number;
    top3WeightPct: number;
    maxSectorWeightPct: number;
    flags: string[];
  };
};

export type AIBriefResponse = {
  bullets: string[];
  disclaimer: string;
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("apter_token");
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

// ─── API Functions ───────────────────────────────────────────────────────────

export async function getPortfolioSummary(
  holdings: HoldingInput[],
  range: string = "1M",
): Promise<PortfolioSummary> {
  const res = await fetch("/api/portfolio/summary", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ holdings, range }),
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function getPortfolioAIBrief(
  holdings: HoldingInput[],
  range: string = "1M",
): Promise<AIBriefResponse> {
  const res = await fetch("/api/portfolio/ai-brief", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ holdings, range }),
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText}`);
  }

  return res.json();
}
