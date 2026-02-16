/**
 * Shared validation utilities for auth forms.
 * Mirrors backend validation rules.
 */

/** Name: 2–50 chars, letters, spaces, hyphens, apostrophes */
const NAME_PATTERN = /^[a-zA-Z\s'\-]{2,50}$/;

export function validateName(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return "Required";
  if (trimmed.length < 2) return "Must be at least 2 characters";
  if (trimmed.length > 50) return "Must be 50 characters or fewer";
  if (!NAME_PATTERN.test(trimmed)) {
    return "Only letters, spaces, hyphens, and apostrophes";
  }
  return null;
}

/** Email: basic format check (server does canonical validation) */
export function validateEmail(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return "Required";
  // Simple but catches most issues; server does authoritative validation
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(trimmed)) return "Enter a valid email address";
  return null;
}

/** Password: minimum 10 characters */
export function validatePassword(value: string): string | null {
  if (!value) return "Required";
  if (value.length < 10) return "Must be at least 10 characters";
  return null;
}

/** Confirm password: must match */
export function validateConfirmPassword(value: string, password: string): string | null {
  if (!value) return "Required";
  if (value !== password) return "Passwords do not match";
  return null;
}

/**
 * Password strength: returns 0–4
 * 0 = too short
 * 1 = weak
 * 2 = fair
 * 3 = good
 * 4 = strong
 */
export function passwordStrength(value: string): number {
  if (value.length < 10) return 0;
  let score = 1;
  if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score++;
  if (/\d/.test(value)) score++;
  if (/[^a-zA-Z0-9]/.test(value)) score++;
  return score;
}

export const STRENGTH_LABELS: Record<number, { label: string; color: string }> = {
  0: { label: "Too short", color: "bg-risk-off" },
  1: { label: "Weak", color: "bg-risk-off" },
  2: { label: "Fair", color: "bg-risk-neutral" },
  3: { label: "Good", color: "bg-risk-on" },
  4: { label: "Strong", color: "bg-risk-on" },
};
