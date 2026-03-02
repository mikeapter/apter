/**
 * Client-side auth token helpers.
 *
 * Access token: stored in localStorage (short-lived, 10 min).
 * Refresh token: stored in an HTTP-only cookie set by the API (not accessible
 * from JS). The browser sends it automatically on /auth/* requests.
 * Session cookie: lightweight indicator for Next.js middleware SSR redirect.
 *
 * The server sets httpOnly cookies (apter_at, apter_refresh) via Set-Cookie
 * headers.  We also set the apter_session indicator cookie client-side
 * because Next.js rewrite proxies can silently drop Set-Cookie headers
 * from external backends.
 */

const LS_TOKEN = "apter_token";
const COOKIE_NAME = "apter_session";
const USER_KEY = "apter_user";

export type StoredUser = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name?: string;
};

export function getToken(): string | null {
  try {
    return localStorage.getItem(LS_TOKEN);
  } catch {
    return null;
  }
}

/**
 * Store auth token in localStorage and set the apter_session indicator cookie.
 *
 * The server also sets apter_session via Set-Cookie, but the route proxy
 * sets it as a belt-and-suspenders measure.  Setting it here ensures
 * Next.js middleware always sees it on subsequent hard navigations.
 */
export function setToken(token: string, remember = false): void {
  try {
    localStorage.setItem(LS_TOKEN, token);
    localStorage.setItem("apter_remember", remember ? "1" : "0");
  } catch {}

  // Set the session indicator cookie for Next.js middleware.
  const secure =
    typeof window !== "undefined" && window.location.protocol === "https:"
      ? "; Secure"
      : "";
  if (remember) {
    document.cookie = `${COOKIE_NAME}=1; path=/; max-age=${30 * 86400}; SameSite=Lax${secure}`;
  } else {
    document.cookie = `${COOKIE_NAME}=1; path=/; SameSite=Lax${secure}`;
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(LS_TOKEN);
    localStorage.removeItem("apter_remember");
  } catch {}
  document.cookie = `${COOKIE_NAME}=; path=/; max-age=0`;
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

export function getStoredUser(): StoredUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StoredUser;
  } catch {
    return null;
  }
}

export function setStoredUser(user: StoredUser): void {
  try {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    // Storage unavailable
  }
}

export function clearStoredUser(): void {
  try {
    localStorage.removeItem(USER_KEY);
  } catch {
    // Storage unavailable
  }
}

export function logout(): void {
  clearToken();
  clearStoredUser();
  // Clear the HTTP-only refresh cookie via the backend
  try {
    fetch("/auth/logout", { method: "POST", credentials: "include" });
  } catch {
    // Fire-and-forget
  }
}
