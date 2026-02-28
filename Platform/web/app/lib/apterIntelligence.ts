/**
 * Apter Intelligence API client — isolated from Market Overview.
 *
 * Calls POST /api/apter-intelligence for live-data-grounded chat.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ApterIntelligenceAnswer = {
  summary: string;
  data_used: string[];
  key_drivers: string[];
  risks: string[];
  what_to_watch: string[];
  explanation: string;
  data_sources: string[];
  disclaimer: string;
};

export type ApterIntelligenceMeta = {
  request_id: string;
  data_quality: "live" | "partial" | "unavailable";
  model?: string;
};

export type ApterIntelligenceResponse = {
  answer: ApterIntelligenceAnswer;
  context: Record<string, unknown>;
  meta: ApterIntelligenceMeta;
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

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

// ---------------------------------------------------------------------------
// Main API call
// ---------------------------------------------------------------------------

const REQUEST_TIMEOUT_MS = 12_000;

export async function askApterIntelligence(
  question: string,
  tickers: string[],
): Promise<ApterIntelligenceResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(`${apiBase()}/api/apter-intelligence`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ question, tickers }),
      signal: controller.signal,
      cache: "no-store",
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      // Try to extract detail from JSON error response
      let detail = text;
      try {
        const parsed = JSON.parse(text);
        detail = parsed.detail || text;
      } catch {
        // Use raw text
      }
      throw new Error(detail || `${res.status} ${res.statusText}`);
    }

    return (await res.json()) as ApterIntelligenceResponse;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Request timed out. Please try again.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}
