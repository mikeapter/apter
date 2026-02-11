// Platform/web/src/lib/api.ts

type JsonPrimitive = string | number | boolean | null;
type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

/**
 * Remove trailing slashes and trim whitespace.
 */
export function normalizeBaseUrl(raw?: string): string {
  const v = (raw ?? "").trim();
  if (!v) return "";
  return v.replace(/\/+$/, "");
}

/**
 * Decide API base URL with safe fallbacks:
 * 1) NEXT_PUBLIC_API_BASE_URL (preferred)
 * 2) In browser on localhost -> local API
 * 3) In browser on production domains -> api.apterfinancial.com
 * 4) Last resort -> empty (relative path)
 */
function resolveApiBaseUrl(): string {
  const envBase = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  if (envBase) return envBase;

  if (typeof window !== "undefined") {
    const host = window.location.hostname.toLowerCase();

    if (host === "localhost" || host === "127.0.0.1" || host === "0.0.0.0") {
      return "http://127.0.0.1:8000";
    }

    return "https://api.apterfinancial.com";
  }

  return "";
}

const API_BASE = resolveApiBaseUrl();

function joinUrl(base: string, path: string): string {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return base ? `${base}${cleanPath}` : cleanPath;
}

function buildHeaders(init?: RequestInit): HeadersInit {
  const headers = new Headers(init?.headers ?? {});
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token =
    typeof window !== "undefined" ? localStorage.getItem("apter_token") : null;

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return headers;
}

function formatNetworkError(err: unknown, url: string): Error {
  const msg =
    err instanceof Error
      ? err.message
      : typeof err === "string"
      ? err
      : "Unknown network error";

  return new Error(
    [
      "Network error while calling API",
      `URL: ${url}`,
      `API_BASE: ${API_BASE || "(empty)"}`,
      `Details: ${msg}`,
      "Hint: verify NEXT_PUBLIC_API_BASE_URL on Apter Web and CORS_ORIGINS on Apter API.",
    ].join(" | ")
  );
}

async function parseResponseBody(res: Response): Promise<JsonValue | string | null> {
  const contentType = res.headers.get("content-type")?.toLowerCase() ?? "";

  if (res.status === 204) return null;

  if (contentType.includes("application/json")) {
    try {
      return (await res.json()) as JsonValue;
    } catch {
      return null;
    }
  }

  try {
    return await res.text();
  } catch {
    return null;
  }
}

export async function fetchJson<T = unknown>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const url = joinUrl(API_BASE, path);
  const headers = buildHeaders(init);

  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers,
      cache: "no-store",
      credentials: "include",
    });
  } catch (err) {
    throw formatNetworkError(err, url);
  }

  const body = await parseResponseBody(res);

  if (!res.ok) {
    const detail =
      typeof body === "string"
        ? body
        : body == null
        ? ""
        : JSON.stringify(body);

    throw new Error(
      `HTTP ${res.status} ${res.statusText} | URL: ${url} | API_BASE: ${
        API_BASE || "(empty)"
      } | Body: ${detail}`
    );
  }

  return body as T;
}

const api = { fetchJson, normalizeBaseUrl };
export default api;
