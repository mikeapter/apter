/**
 * Client-side auth token helpers.
 *
 * Access token: stored in localStorage (short-lived, 10 min).
 * Refresh token: stored in localStorage AND as an HTTP-only cookie.
 *   localStorage is the primary source for refresh because Next.js
 *   proxy rewrites can silently drop Set-Cookie headers.
 * Session cookie: lightweight indicator for Next.js middleware SSR redirect.
 */

const LS_TOKEN = "apter_token";
const LS_REFRESH = "apter_refresh_token";
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

export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(LS_REFRESH);
  } catch {
    return null;
  }
}

/**
 * Store auth tokens in localStorage and set the apter_session indicator cookie.
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

/**
 * Store the refresh token in localStorage so the client can send it
 * in the request body on /auth/refresh, bypassing cookie issues.
 */
export function setRefreshToken(token: string): void {
  try {
    localStorage.setItem(LS_REFRESH, token);
  } catch {}
}

export function clearToken(): void {
  try {
    localStorage.removeItem(LS_TOKEN);
    localStorage.removeItem(LS_REFRESH);
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
