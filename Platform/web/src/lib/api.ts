// Platform/web/src/lib/api.ts

export function normalizeBaseUrl(raw?: string): string {
  const v = (raw ?? "").trim();
  if (!v) return "";
  return v.replace(/\/+$/, "");
}

const API_BASE = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

function joinUrl(base: string, path: string): string {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return base ? `${base}${cleanPath}` : cleanPath;
}

export async function fetchJson<T = unknown>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const url = joinUrl(API_BASE, path);

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(init?.headers ?? {}),
  };

  const token =
    typeof window !== "undefined" ? localStorage.getItem("apter_token") : null;

  if (token) {
    (headers as Record<string, string>).Authorization = `Bearer ${token}`;
  }

  const res = await fetch(url, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText} :: ${text}`);
  }

  return (await res.json()) as T;
}

// compatibility export
const api = { fetchJson, normalizeBaseUrl };
export default api;
