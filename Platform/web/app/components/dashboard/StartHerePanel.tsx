"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
import Link from "next/link";
import { Eye, Search, BarChart3, Sparkles } from "lucide-react";

const PORTFOLIO_LS_KEY = "apter_portfolio";
const WATCHLIST_LS_KEY = "apter_watchlist";
const DISMISS_LS_KEY = "apter_start_here_dismissed";

const STEPS = [
  {
    num: 1,
    title: "Add stocks you follow",
    description: "Build a watchlist of 3\u20135 tickers to track grades, price moves, and signals.",
    href: "/watchlist",
    cta: "Go to Watchlist",
    icon: Eye,
  },
  {
    num: 2,
    title: "Review conviction & pillar breakdown",
    description: "Use the screener to compare conviction scores and see what drives each grade.",
    href: "/screener",
    cta: "Open Screener",
    icon: Search,
  },
  {
    num: 3,
    title: "Check market regime & movers",
    description: "The dashboard shows the current regime, top movers, and your portfolio at a glance.",
    href: "/dashboard",
    cta: "View Dashboard",
    icon: BarChart3,
  },
  {
    num: 4,
    title: "Read the AI brief",
    description: "Get an AI-generated overview of market conditions and your selected tickers.",
    href: "/dashboard/ai-overview",
    cta: "AI Overview",
    icon: Sparkles,
  },
] as const;

export function StartHerePanel() {
  const [dismissed, setDismissed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(DISMISS_LS_KEY) === "1") {
      setDismissed(true);
    }
    // Small delay so animation plays after mount
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  function handleDismiss() {
    setDismissed(true);
    try { localStorage.setItem(DISMISS_LS_KEY, "1"); } catch {}
  }

  if (dismissed) return null;

  return (
    <section
      className="bt-panel p-5 sm:p-6 max-w-3xl space-y-5 transition-all duration-500 ease-out"
      style={{
        opacity: mounted ? 1 : 0,
        transform: mounted ? "translateY(0)" : "translateY(8px)",
      }}
    >
      <div className="flex items-center justify-between">
        <h2 className="bt-panel-title">Start Here</h2>
        <button
          type="button"
          onClick={handleDismiss}
          className="text-muted-foreground hover:text-foreground text-xs"
        >
          Dismiss
        </button>
      </div>

      <p className="text-sm text-muted-foreground leading-relaxed">
        Your portfolio and watchlist are empty. Follow these steps to get the most out of the platform.
      </p>

      <ol className="grid gap-3 sm:grid-cols-2">
        {STEPS.map((step) => {
          const Icon = step.icon;
          return (
            <li key={step.num} className="rounded-md border border-border bg-panel-2 p-4 flex flex-col gap-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Icon size={15} className="text-muted-foreground shrink-0" />
                <span className="font-mono text-muted-foreground text-xs">{step.num}.</span>
                {step.title}
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">{step.description}</p>
              <Link href={step.href} className="bt-button mt-auto self-start text-xs gap-1.5 px-2.5 py-1.5">
                {step.cta}
              </Link>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Reactive hook: hides StartHerePanel as soon as data appears       */
/* ------------------------------------------------------------------ */

function lsHasItems(key: string): boolean {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return false;
    const arr = JSON.parse(raw);
    return Array.isArray(arr) && arr.length > 0;
  } catch {
    return false;
  }
}

function checkEmpty(): boolean {
  return !lsHasItems(PORTFOLIO_LS_KEY) && !lsHasItems(WATCHLIST_LS_KEY);
}

// Listeners subscribed to storage changes
let listeners: Array<() => void> = [];
let cachedEmpty = true; // SSR-safe default

function subscribe(cb: () => void) {
  listeners = [...listeners, cb];
  return () => { listeners = listeners.filter((l) => l !== cb); };
}

function emitChange() {
  cachedEmpty = checkEmpty();
  listeners.forEach((l) => l());
}

// Patch localStorage.setItem once so we detect in-tab writes
if (typeof window !== "undefined") {
  cachedEmpty = checkEmpty();

  const originalSetItem = localStorage.setItem.bind(localStorage);
  localStorage.setItem = function (key: string, value: string) {
    originalSetItem(key, value);
    if (key === PORTFOLIO_LS_KEY || key === WATCHLIST_LS_KEY) {
      emitChange();
    }
  };

  // Also listen for cross-tab changes
  window.addEventListener("storage", (e) => {
    if (e.key === PORTFOLIO_LS_KEY || e.key === WATCHLIST_LS_KEY) {
      emitChange();
    }
  });
}

function getSnapshot(): boolean {
  return cachedEmpty;
}

function getServerSnapshot(): boolean {
  return true; // assume empty on server (panel hidden until client hydrates)
}

/**
 * Returns true when both portfolio and watchlist are empty.
 * Reactively updates when localStorage changes (same tab or cross-tab).
 */
export function useIsEmptyAccount(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
