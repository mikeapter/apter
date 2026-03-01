import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = new Set(["/", "/login", "/signup", "/register", "/forgot-password", "/plans", "/terms", "/privacy", "/disclaimer"]);

const PUBLIC_PREFIXES = ["/api/", "/auth/", "/v1/", "/2fa/", "/_next/", "/favicon", "/logo"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths
  if (PUBLIC_PATHS.has(pathname)) return NextResponse.next();

  // Allow public prefixes (API, assets, etc.)
  if (PUBLIC_PREFIXES.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Check for session indicator cookie (set by server and client)
  // The server sets apter_session=1 alongside the httpOnly auth cookies.
  // We also check apter_rt as a fallback since it's httpOnly but readable by middleware.
  const hasSession = request.cookies.get("apter_session") || request.cookies.get("apter_rt");

  if (!hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
