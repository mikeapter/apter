/**
 * Typed Apter Intelligence API client with SSE streaming support.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AIResponse = {
  message_id?: string;
  summary: string;
  data_used: string[];
  explanation: string;
  watchlist_items: string[];
  risk_flags: string[];
  checklist: string[];
  disclaimer: string;
  citations: string[];
  scenarios?: string[] | null;
  comparisons?: string[] | null;
  cached?: boolean;
};

export type ChatRequest = {
  message: string;
  context?: {
    tickers?: string[];
    view?: string;
  };
};

export type FeedbackRequest = {
  message_id: string;
  rating: "helpful" | "not_helpful";
  notes?: string;
};

export type SSEEvent =
  | { type: "start"; message_id: string }
  | { type: "token"; content: string }
  | { type: "replace"; content: string }
  | { type: "done"; message_id: string; full_text: string };

// Stock Intelligence Brief types
export type RiskTag = { category: string; level: "Low" | "Moderate" | "Elevated" };

export type StockIntelligenceBrief = {
  ticker: string;
  executive_summary: string;
  key_drivers: string[];
  risk_tags: RiskTag[];
  regime_context: string;
  what_to_monitor: string[];
  snapshot: Record<string, string | number | null>;
  as_of: string;
  disclaimer: string;
  data_sources: string[];
  cached?: boolean;
};

// Market Intelligence Brief types
export type MarketIntelligenceBrief = {
  executive_summary: string;
  risk_dashboard: {
    regime: string;
    volatility_context: string;
    breadth_context: string;
  };
  catalysts: string[];
  what_changed: string[];
  as_of: string;
  disclaimer: string;
  data_sources: string[];
  cached?: boolean;
};

// Apter Rating types
export type AptRatingComponent = {
  score: number;
  weight: number;
  drivers: string[];
};

export type AptRatingResponse = {
  ticker: string;
  rating: number;
  band: string;
  components: {
    growth: AptRatingComponent;
    profitability: AptRatingComponent;
    balance_sheet: AptRatingComponent;
    momentum: AptRatingComponent;
    risk: AptRatingComponent;
  };
  as_of: string;
  disclaimer: string;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function apiBase(): string {
  const pub = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (pub && pub.trim().length > 0) return pub.replace(/\/+$/, "");
  if (typeof window !== "undefined") return "";
  const srv = process.env.API_BASE_URL;
  if (srv && srv.trim().length > 0) return srv.replace(/\/+$/, "");
  return "http://127.0.0.1:3000";
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("apter_token");
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extra,
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

// ---------------------------------------------------------------------------
// Chat (JSON)
// ---------------------------------------------------------------------------

export async function chatJSON(req: ChatRequest): Promise<AIResponse> {
  const res = await fetch(`${apiBase()}/api/ai/chat`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(req),
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText}`);
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Chat (SSE streaming)
// ---------------------------------------------------------------------------

export async function chatStream(
  req: ChatRequest,
  callbacks: {
    onToken: (token: string) => void;
    onStart?: (messageId: string) => void;
    onReplace?: (json: AIResponse) => void;
    onDone?: (messageId: string, fullText: string) => void;
    onError?: (error: Error) => void;
  },
): Promise<void> {
  const res = await fetch(`${apiBase()}/api/ai/chat`, {
    method: "POST",
    headers: authHeaders({ Accept: "text/event-stream" }),
    body: JSON.stringify(req),
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    callbacks.onError?.(new Error(text || `${res.status}`));
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    callbacks.onError?.(new Error("No response body"));
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6).trim();
        if (payload === "[DONE]") return;

        try {
          const event = JSON.parse(payload) as SSEEvent;
          switch (event.type) {
            case "start":
              callbacks.onStart?.(event.message_id);
              break;
            case "token":
              callbacks.onToken(event.content);
              break;
            case "replace":
              try {
                const parsed = JSON.parse(event.content) as AIResponse;
                callbacks.onReplace?.(parsed);
              } catch {
                callbacks.onToken(event.content);
              }
              break;
            case "done":
              callbacks.onDone?.(event.message_id, event.full_text);
              break;
          }
        } catch {
          // skip malformed events
        }
      }
    }
  } catch (err) {
    callbacks.onError?.(err instanceof Error ? err : new Error(String(err)));
  }
}

// ---------------------------------------------------------------------------
// Overview (legacy)
// ---------------------------------------------------------------------------

export async function fetchOverview(
  tickers?: string[],
  timeframe: "daily" | "weekly" = "daily",
): Promise<AIResponse> {
  const params = new URLSearchParams();
  if (tickers?.length) params.set("tickers", tickers.join(","));
  params.set("timeframe", timeframe);

  const res = await fetch(
    `${apiBase()}/api/ai/overview?${params.toString()}`,
    { method: "GET", headers: authHeaders(), cache: "no-store" },
  );

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText}`);
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Stock Intelligence Brief
// ---------------------------------------------------------------------------

export async function fetchStockIntelligence(
  ticker: string,
): Promise<StockIntelligenceBrief> {
  const res = await fetch(
    `${apiBase()}/api/ai/intelligence/stock?ticker=${encodeURIComponent(ticker)}`,
    { method: "GET", headers: authHeaders(), cache: "no-store" },
  );

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText}`);
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Market Intelligence Brief
// ---------------------------------------------------------------------------

export async function fetchMarketIntelligence(
  mode: "daily" | "weekly" = "daily",
): Promise<MarketIntelligenceBrief> {
  const res = await fetch(
    `${apiBase()}/api/ai/intelligence/market?mode=${mode}`,
    { method: "GET", headers: authHeaders(), cache: "no-store" },
  );

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText}`);
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Apter Rating
// ---------------------------------------------------------------------------

export async function fetchAptRating(
  ticker: string,
): Promise<AptRatingResponse> {
  const res = await fetch(
    `${apiBase()}/api/rating/${encodeURIComponent(ticker)}`,
    { method: "GET", headers: authHeaders(), cache: "no-store" },
  );

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText}`);
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Feedback
// ---------------------------------------------------------------------------

export async function sendFeedback(req: FeedbackRequest): Promise<void> {
  const res = await fetch(`${apiBase()}/api/ai/feedback`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(req),
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText}`);
  }
}
