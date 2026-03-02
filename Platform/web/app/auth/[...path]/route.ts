/**
 * Auth proxy route handler.
 *
 * Next.js rewrites to external backends can silently drop Set-Cookie
 * response headers.  This route handler explicitly proxies /auth/*
 * requests to the FastAPI backend and forwards ALL response headers
 * — including every Set-Cookie — back to the browser.
 *
 * Because filesystem routes take precedence over rewrites, this
 * handler supersedes the /auth/:path* rewrite in next.config.mjs.
 */

import { NextRequest } from "next/server";

const API_URL = (
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/+$/, "");

async function proxy(
  request: NextRequest,
  { params }: { params: { path: string[] } },
) {
  const path = params.path.join("/");
  const upstream = new URL(`/auth/${path}`, API_URL);

  // Forward query parameters
  request.nextUrl.searchParams.forEach((value, key) => {
    upstream.searchParams.set(key, value);
  });

  // Forward request headers (skip hop-by-hop)
  const reqHeaders = new Headers();
  const skip = new Set(["host", "connection", "transfer-encoding", "keep-alive"]);
  request.headers.forEach((value, key) => {
    if (!skip.has(key.toLowerCase())) {
      reqHeaders.set(key, value);
    }
  });

  // Build fetch options
  const init: RequestInit & { duplex?: string } = {
    method: request.method,
    headers: reqHeaders,
    cache: "no-store",
  };

  // Forward body for methods that carry one
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
    init.duplex = "half";
  }

  const res = await fetch(upstream.toString(), init);

  // ── Build response, explicitly forwarding Set-Cookie ──────────────
  const resHeaders = new Headers();
  const hopByHop = new Set(["connection", "transfer-encoding", "keep-alive"]);

  res.headers.forEach((value, key) => {
    if (hopByHop.has(key.toLowerCase())) return;
    if (key.toLowerCase() === "set-cookie") return; // handle below
    resHeaders.set(key, value);
  });

  // getSetCookie() returns each Set-Cookie as a separate string —
  // Headers.forEach() would merge them into one comma-separated value
  // which browsers cannot parse correctly.
  const cookies =
    typeof res.headers.getSetCookie === "function"
      ? res.headers.getSetCookie()
      : (res.headers.get("set-cookie") || "").split(/,(?=\s*\w+=)/).filter(Boolean);

  for (const c of cookies) {
    resHeaders.append("set-cookie", c);
  }

  return new Response(await res.arrayBuffer(), {
    status: res.status,
    statusText: res.statusText,
    headers: resHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const PATCH = proxy;
