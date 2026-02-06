// Platform/web/src/lib/api.ts
export const API_BASE =
  (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

type Json = Record<string, unknown> | Array<unknown> | string | number | boolean | null;

async function request<T = Json>(
  path: string,
  init?: RequestInit & { token?: string | null }
): Promise<T> {
  const url = `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;

  const headers = new Headers(init?.headers || {});
  headers.set("Content-Type", "application/json");

  if (init?.token) {
    headers.set("Authorization", `Bearer ${init.token}`);
  }

  const res = await fetch(url, {
    ...init,
    headers,
    cache: "no-store",
  });

  const text = await res.text();
  const data = text ? safeJsonParse(text) : null;

  if (!res.ok) {
    const detail =
      (isObject(data) && typeof data.detail === "string" && data.detail) ||
      `HTTP ${res.status}`;
    throw new Error(detail);
  }

  return data as T;
}

function safeJsonParse(text: string): Json {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function isObject(v: unknown): v is Record<string, any> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** Auth */
export function register(email: string, password: string) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string) {
  return request<{ access_token: string; token_type: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username: email, password }),
  });
}

/** Dashboard */
export function getDashboard(period: "today" | "week" | "month" = "today") {
  return request(`/api/dashboard?period=${encodeURIComponent(period)}`);
}

/** Subscriptions */
export function getPlans() {
  // IMPORTANT: Swagger shows /api/plans as public route
  return request("/api/plans");
}

export function getMySubscription(token: string) {
  return request("/api/subscription/me", { token });
}

export function devSetTier(tier: string, devKey: string, token: string) {
  return request("/api/subscription/dev/set-tier", {
    method: "POST",
    token,
    headers: {
      "X-Admin-Key": devKey,
    },
    body: JSON.stringify({ tier }),
  });
}

/** Signals */
export function getSignalsFeed(limit = 25, token?: string | null) {
  return request(`/v1/signals/feed?limit=${limit}`, { token: token || null });
}
