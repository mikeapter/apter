export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; status?: number };

function normalizeBase(u: string) {
  return u.replace(/\/+$/, "");
}

/**
 * Option A behavior:
 * - Browser/client: call same-origin Next route handlers ("/api/...", "/v1/...")
 * - Server: default to Next dev server unless API_BASE_URL is explicitly set
 * - If you ever want to point the browser to a different backend, set NEXT_PUBLIC_API_BASE_URL
 */
function baseUrl() {
  const publicBase = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (publicBase && publicBase.trim().length > 0) return normalizeBase(publicBase);

  // Client-side: same origin
  if (typeof window !== "undefined") return "";

  // Server-side: allow override, else default to local Next dev server
  const serverBase = process.env.API_BASE_URL;
  if (serverBase && serverBase.trim().length > 0) return normalizeBase(serverBase);

  return "http://127.0.0.1:3000";
}

function buildUrl(path: string) {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl()}${p}`;
}

function mergedHeaders(initHeaders: HeadersInit | undefined, token?: string) {
  const h = new Headers(initHeaders || undefined);

  // Only set if not already provided
  if (!h.has("Content-Type")) h.set("Content-Type", "application/json");

  if (token) h.set("Authorization", `Bearer ${token}`);

  return h;
}

export async function apiGet<T>(
  path: string,
  init?: RequestInit,
  token?: string
): Promise<ApiResult<T>> {
  const url = buildUrl(path);

  try {
    const res = await fetch(url, {
      ...init,
      method: "GET",
      headers: mergedHeaders(init?.headers, token),
      cache: "no-store",
    });

    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      return {
        ok: false,
        error: txt || `${res.status} ${res.statusText}`,
        status: res.status,
      };
    }

    const data = (await res.json()) as T;
    return { ok: true, data };
  } catch (e: any) {
    return { ok: false, error: e?.message || "Network error" };
  }
}

export async function apiPost<T>(
  path: string,
  body: any,
  init?: RequestInit,
  token?: string
): Promise<ApiResult<T>> {
  const url = buildUrl(path);

  try {
    const res = await fetch(url, {
      ...init,
      method: "POST",
      headers: mergedHeaders(init?.headers, token),
      body: JSON.stringify(body ?? {}),
      cache: "no-store",
    });

    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      return {
        ok: false,
        error: txt || `${res.status} ${res.statusText}`,
        status: res.status,
      };
    }

    const data = (await res.json()) as T;
    return { ok: true, data };
  } catch (e: any) {
    return { ok: false, error: e?.message || "Network error" };
  }
}
