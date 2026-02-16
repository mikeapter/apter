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
};

export function getToken(): string | null {
  try {
    return localStorage.getItem(LS_TOKEN);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(LS_TOKEN, token);
  } catch {}
  const secure =
    typeof window !== "undefined" && window.location.protocol === "https:"
      ? "; Secure"
      : "";
  document.cookie = `${COOKIE_NAME}=1; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax${secure}`;
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
