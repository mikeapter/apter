// Platform/web/src/lib/api.ts

export type Json = Record<string, unknown> | unknown[] | string | number | boolean | null;

const RAW_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "").trim();

// Normalize base once.
// - remove trailing slashes
// - remove accidental trailing /api (we add /api in buildApiUrl)
const BASE = RAW_BASE.replace(/\/+$/, "").replace(/\/api$/i, "");

function buildApiUrl(path: string): string {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;

  // If caller already passed /api/..., keep it
  if (cleanPath.startsWith("/api/")) {
    return `${BASE}${cleanPath}`;
  }

  // Otherwise prepend /api
  return `${BASE}/api${cleanPath}`;
}

export class ApiError extends Error {
  status: number;
  bodyText: string;

  constructor(message: string, status: number, bodyText: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.bodyText = bodyText;
  }
}

export async function apiFetch<T = Json>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const url = buildApiUrl(path);

  const headers = new Headers(init.headers || {});
  if (!headers.has("Content-Type") && init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const token =
    typeof window !== "undefined" ? localStorage.getItem("apter_token") : null;
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(url, {
    ...init,
    headers,
    cache: "no-store",
  });

  const text = await res.text();

  if (!res.ok) {
    throw new ApiError(
      `API ${res.status} ${res.statusText} at ${url}`,
      res.status,
      text
    );
  }

  // Empty body handling
  if (!text) return null as T;

  try {
    return JSON.parse(text) as T;
  } catch {
    // non-JSON successful response fallback
    return text as T;
  }
}

export function getApiBaseForDebug() {
  return { RAW_BASE, BASE };
}
