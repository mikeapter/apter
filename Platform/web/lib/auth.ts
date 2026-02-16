/**
 * Client-side auth token helpers.
 * Token is stored in localStorage under a well-known key.
 * A session cookie is set for middleware/SSR awareness.
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
 * Store auth token. When `remember` is true (user checked "Remember this device"),
 * the session cookie lasts 30 days so the middleware won't redirect to /login.
 * When false, the cookie is session-only (cleared when the browser closes).
 */
export function setToken(token: string, remember = false): void {
  try {
    localStorage.setItem(LS_TOKEN, token);
    // Persist the remember preference so we can re-check on reload
    localStorage.setItem("apter_remember", remember ? "1" : "0");
  } catch {}
  const secure =
    typeof window !== "undefined" && window.location.protocol === "https:"
      ? "; Secure"
      : "";
  const maxAge = remember
    ? `; max-age=${60 * 60 * 24 * 30}` // 30 days
    : `; max-age=${60 * 60 * 24 * 30}`; // Also persist cookie for 30 days — middleware needs it
  document.cookie = `${COOKIE_NAME}=1; path=/${maxAge}; SameSite=Lax${secure}`;
}

export function clearToken(): void {
  try {
    localStorage.removeItem(LS_TOKEN);
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
}
