// Platform/web/src/lib/api.ts

export type Json = Record<string, unknown> | unknown[] | string | number | boolean | null;

function stripTrailingSlash(url: string): string {
  return url.replace(/\/+$/, "");
}

function getBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!raw) {
    // Browser fallback so app still works locally
    if (typeof window !== "undefined") return window.location.origin;
    return "http://127.0.0.1:8000";
  }
  return stripTrailingSlash(raw);
}

export const API_BASE_URL = getBaseUrl();

function withQuery(path: string, query?: Record<string, string | number | boolean | undefined>) {
  if (!query) return path;
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined) usp.set(k, String(v));
  }
  const qs = usp.toString();
  return qs ? `${path}?${qs}` : path;
}

async function fetchJson(
  path: string,
  init?: RequestInit,
  opts?: { token?: string; adminKey?: string; allow404?: boolean }
): Promise<Json> {
  const headers = new Headers(init?.headers || {});
  headers.set("Accept", "application/json");
  headers.set("Content-Type", "application/json");

  if (opts?.token) headers.set("Authorization", `Bearer ${opts.token}`);
  if (opts?.adminKey) headers.set("X-Admin-Key", opts.adminKey);

  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    if (opts?.allow404 && res.status === 404) {
      return { detail: "Not Found", _status: 404 };
    }

    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      const detail =
        (body as any)?.detail ||
        (body as any)?.message ||
        JSON.stringify(body);
      message = `${message}: ${detail}`;
    } catch {
      try {
        const txt = await res.text();
        if (txt) message = `${message}: ${txt}`;
      } catch {}
    }
    throw new Error(message);
  }

  try {
    return await res.json();
  } catch {
    return null;
  }
}

// -------- Public helpers --------

export async function getHealth() {
  return fetchJson("/api/health");
}

export async function getDashboard() {
  return fetchJson("/api/dashboard");
}

/**
 * Plans endpoint can vary by build/version.
 * Try modern first, then fallback.
 */
export async function getPlans() {
  // Primary: shown in your Swagger
  const a = (await fetchJson("/api/plans", undefined, { allow404: true })) as any;
  if (!(a && a._status === 404)) return a;

  // Fallback for older wiring
  return fetchJson("/api/subscription/plans");
}

export async function register(email: string, password: string) {
  return fetchJson("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, planTier: "free" }),
  });
}

export async function login(email: string, password: string) {
  return fetchJson("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password, trust_device: false }),
  });
}

export async function getMySubscription(token: string) {
  return fetchJson("/api/subscription/me", undefined, { token });
}

export async function getSignalsFeed(limit = 5, token?: string) {
  // New path in your Swagger
  const p1 = withQuery("/v1/signals/feed", { limit });
  const a = (await fetchJson(p1, undefined, { token, allow404: true })) as any;
  if (!(a && a._status === 404)) return a;

  // Legacy fallback
  const p2 = withQuery("/api/signals/feed", { limit });
  return fetchJson(p2, undefined, { token });
}

export async function devSetTier(
  token: string,
  tier: "free" | "analyst" | "pro",
  adminKey: string
) {
  return fetchJson("/api/subscription/dev/set-tier", {
    method: "POST",
    body: JSON.stringify({ tier }),
  }, { token, adminKey });
}
