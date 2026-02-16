/**
 * Analytics abstraction layer.
 *
 * If no analytics provider is configured, all calls are no-ops.
 * To integrate a provider (e.g. Segment, Mixpanel, PostHog), implement
 * the AnalyticsProvider interface and set it via `setProvider()`.
 */

export type AnalyticsEvent =
  | "landing_view"
  | "cta_get_started_click"
  | "signup_started"
  | "signup_completed"
  | "login_started"
  | "login_completed";

interface AnalyticsProvider {
  track(event: AnalyticsEvent, properties?: Record<string, unknown>): void;
  identify(userId: string, traits?: Record<string, unknown>): void;
  page(name?: string, properties?: Record<string, unknown>): void;
}

const noopProvider: AnalyticsProvider = {
  track: () => {},
  identify: () => {},
  page: () => {},
};

let currentProvider: AnalyticsProvider = noopProvider;

export function setAnalyticsProvider(provider: AnalyticsProvider) {
  currentProvider = provider;
}

export function track(event: AnalyticsEvent, properties?: Record<string, unknown>) {
  try {
    currentProvider.track(event, properties);
  } catch {
    // Silently ignore analytics failures
  }
}

export function identify(userId: string, traits?: Record<string, unknown>) {
  try {
    currentProvider.identify(userId, traits);
  } catch {
    // Silently ignore analytics failures
  }
}

export function page(name?: string, properties?: Record<string, unknown>) {
  try {
    currentProvider.page(name, properties);
  } catch {
    // Silently ignore analytics failures
  }
}
