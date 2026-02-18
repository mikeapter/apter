/**
 * Resilient fetch wrapper with auth token refresh.
 * - On 401: refresh token once, retry original request
 * - On network error/timeout/5xx: DO NOT logout, show transient error
 * - Prevents refresh storms across tabs with in-memory lock
 */

import { getToken, setToken, clearToken, clearStoredUser } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";
const TIMEOUT_MS = 12_000;

// Refresh lock to prevent concurrent refreshes
let _refreshing: Promise<string | null> | null = null;

function buildUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE}${p}`;
}

async function refreshAccessToken(): Promise<string | null> {
  const token = getToken();
  if (!token) return null;

  try {
    const res = await fetch(buildUrl("/auth/refresh"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      cache: "no-store",
    });

    if (!res.ok) return null;

    const data = await res.json();
    if (data.access_token) {
      const remember = typeof window !== "undefined"
        ? localStorage.getItem("apter_remember") === "1"
        : false;
      setToken(data.access_token, remember);
      return data.access_token;
    }
    return null;
  } catch {
    return null;
  }
}

async function getRefreshedToken(): Promise<string | null> {
  // Prevent multiple concurrent refreshes
  if (_refreshing) return _refreshing;

  _refreshing = refreshAccessToken().finally(() => {
    _refreshing = null;
  });

  return _refreshing;
}

function forceLogout(): void {
  clearToken();
  clearStoredUser();
  if (typeof window !== "undefined") {
    const next = encodeURIComponent(window.location.pathname);
    window.location.href = `/login?next=${next}`;
  }
}

export type FetchResult<T> =
  | { ok: true; data: T; status: number }
  | { ok: false; error: string; status?: number; transient?: boolean };

export async function fetchWithAuth<T>(
  path: string,
  options: RequestInit = {},
): Promise<FetchResult<T>> {
  const token = getToken();
  const url = buildUrl(path);

  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !options.body?.constructor?.name?.includes("FormData")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // AbortController for timeout
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const res = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
      cache: "no-store",
    });

    clearTimeout(timeout);

    // Success
    if (res.ok) {
      const data = (await res.json()) as T;
      return { ok: true, data, status: res.status };
    }

    // 401: Try refresh once
    if (res.status === 401) {
      const newToken = await getRefreshedToken();
      if (newToken) {
        // Retry with new token
        headers.set("Authorization", `Bearer ${newToken}`);
        const retryRes = await fetch(url, {
          ...options,
          headers,
          cache: "no-store",
        });

        if (retryRes.ok) {
          const data = (await retryRes.json()) as T;
          return { ok: true, data, status: retryRes.status };
        }

        // Retry also 401 -> genuine auth failure
        if (retryRes.status === 401) {
          forceLogout();
          return { ok: false, error: "Session expired", status: 401 };
        }
      } else {
        // Refresh failed -> genuine auth failure
        forceLogout();
        return { ok: false, error: "Session expired", status: 401 };
      }
    }

    // 5xx: Transient — DO NOT logout
    if (res.status >= 500) {
      const txt = await res.text().catch(() => "");
      return { ok: false, error: txt || "Server error", status: res.status, transient: true };
    }

    // Other errors (400, 403, 404, etc.)
    const txt = await res.text().catch(() => "");
    return { ok: false, error: txt || `${res.status} ${res.statusText}`, status: res.status };

  } catch (e: any) {
    clearTimeout(timeout);

    // Network error or timeout — DO NOT logout
    const isTimeout = e?.name === "AbortError";
    return {
      ok: false,
      error: isTimeout ? "Request timed out" : (e?.message || "Network error"),
      transient: true,
    };
  }
}

export async function authGet<T>(path: string): Promise<FetchResult<T>> {
  return fetchWithAuth<T>(path, { method: "GET" });
}

export async function authPost<T>(path: string, body: any): Promise<FetchResult<T>> {
  return fetchWithAuth<T>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function authPut<T>(path: string, body: any): Promise<FetchResult<T>> {
  return fetchWithAuth<T>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}
