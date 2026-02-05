export type AlertSeverity = "info" | "advisory" | "notice";

export type AlertCategory =
  | "system"
  | "account"
  | "subscription"
  | "data"
  | "security";

export type AlertItem = {
  id: string;
  createdAtISO: string; // ISO string
  severity: AlertSeverity;
  category: AlertCategory;
  title: string; // neutral wording
  body?: string; // optional detail
};

export type AlertPrefs = {
  enabled: boolean;
  mutedCategories: Record<AlertCategory, boolean>;
};

const PREFS_KEY = "apter_alert_prefs_v1";

export function defaultPrefs(): AlertPrefs {
  return {
    enabled: true,
    mutedCategories: {
      system: false,
      account: false,
      subscription: false,
      data: false,
      security: false,
    },
  };
}

export function loadPrefs(): AlertPrefs {
  if (typeof window === "undefined") return defaultPrefs();
  try {
    const raw = window.localStorage.getItem(PREFS_KEY);
    if (!raw) return defaultPrefs();
    const parsed = JSON.parse(raw) as AlertPrefs;
    // Basic hardening:
    const base = defaultPrefs();
    return {
      enabled: typeof parsed.enabled === "boolean" ? parsed.enabled : base.enabled,
      mutedCategories: { ...base.mutedCategories, ...(parsed.mutedCategories || {}) },
    };
  } catch {
    return defaultPrefs();
  }
}

export function savePrefs(prefs: AlertPrefs) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
}

export function shouldShowAlert(alert: AlertItem, prefs: AlertPrefs): boolean {
  if (!prefs.enabled) return false;
  if (prefs.mutedCategories[alert.category]) return false;
  return true;
}
