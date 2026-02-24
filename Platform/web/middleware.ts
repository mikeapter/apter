import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = new Set(["/", "/login", "/signup", "/register", "/forgot-password", "/reset-password", "/plans", "/terms", "/privacy", "/disclaimer", "/risk-disclosure", "/contact", "/about"]);

const PUBLIC_PREFIXES = ["/api/", "/auth/", "/v1/", "/2fa/", "/_next/", "/favicon", "/logo"];

// Build connect-src dynamically to include the API origin if set
const _apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "";
const _connectSrc = _apiBase ? `connect-src 'self' ${_apiBase}` : "connect-src 'self'";

// Content Security Policy for the frontend
const CSP_DIRECTIVES = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",           // Next.js hydration requires inline scripts
  "style-src 'self' 'unsafe-inline'",             // Next.js + Tailwind use inline styles
  "img-src 'self' data: blob: https:",            // Allow images from self, data URIs, and HTTPS
  "font-src 'self'",
  _connectSrc,                                    // API calls (same-origin + API base if set)
  "frame-ancestors 'none'",                       // Prevent clickjacking
  "base-uri 'self'",                              // Prevent base tag injection
  "form-action 'self'",                           // Restrict form submissions
  "object-src 'none'",                            // Block plugins (Flash, etc.)
].join("; ");

function addSecurityHeaders(response: NextResponse): NextResponse {
  response.headers.set("Content-Security-Policy", CSP_DIRECTIVES);
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()");
  response.headers.set("X-XSS-Protection", "0");
  return response;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public paths
  if (PUBLIC_PATHS.has(pathname)) {
    return addSecurityHeaders(NextResponse.next());
  }

  // Allow public prefixes (API, assets, etc.)
  if (PUBLIC_PREFIXES.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Check for session indicator cookie
  const hasSession = request.cookies.get("apter_session");

  if (!hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return addSecurityHeaders(NextResponse.next());
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
