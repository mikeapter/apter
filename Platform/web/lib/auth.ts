/**
 * Client-side auth token helpers.
 *
 * Access token: stored in localStorage (short-lived, 10 min).
 * Refresh token: stored in an HTTP-only cookie set by the API (not accessible
 * from JS). The browser sends it automatically on /auth/* requests.
 * Session cookie: lightweight indicator for Next.js middleware SSR redirect.
 *
 * The server owns all cookie management (apter_at, apter_refresh, apter_session)
 * via Set-Cookie headers. We do NOT set cookies client-side to avoid
 * overwriting the server's persistent cookie settings.
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
 * Store auth token in localStorage for backward compat.
 *
 * The server owns all cookie management (apter_at, apter_refresh, apter_session)
 * via Set-Cookie headers. We do NOT set apter_session here to avoid
 * overwriting the server's persistent cookie with a session cookie.
 */
export function setToken(token: string, remember = false): void {
  try {
    localStorage.setItem(LS_TOKEN, token);
    localStorage.setItem("apter_remember", remember ? "1" : "0");
  } catch {}
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
