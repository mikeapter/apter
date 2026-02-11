"use client";

import { useEffect, useMemo, useState } from "react";
import { useDashboardData } from "../../providers/DashboardDataProvider";
import type { MarketRegime } from "../../lib/dashboard";

function regimeChipClass(regime: MarketRegime) {
  if (regime === "RISK-ON") return "bt-chip bt-chip-on";
  if (regime === "RISK-OFF") return "bt-chip bt-chip-off";
  return "bt-chip bt-chip-neutral";
}

function formatAge(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000));
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

function BrandMark() {
  return (
    <div className="h-8 w-8 rounded-full border border-border flex items-center justify-center">
      <span className="text-[12px] font-semibold tracking-[0.06em]">A</span>
    </div>
  );
}

function DisclosureBanner() {
  return (
    <div className="w-full border-b border-border bg-panel-2 px-4 py-2">
      <p className="text-[11px] md:text-xs text-muted-foreground tracking-[0.01em]">
        Information is for educational and research purposes only. Not investment advice.
        Apter Financial is not acting as a registered investment adviser.
      </p>
    </div>
  );
}

export function Topbar({ onOpenMobile }: { onOpenMobile: () => void }) {
  const { data, lastUpdatedAt, source, error } = useDashboardData();

  // IMPORTANT: start as null to prevent server/client mismatch (hydration error)
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const timestamp = useMemo(() => {
    if (now === null) return "—";
    const d = new Date(now);
    return new Intl.DateTimeFormat("en-US", {
      weekday: "short",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
      timeZoneName: "short",
    }).format(d);
  }, [now]);

  const age =
    now === null || lastUpdatedAt === 0 ? "--:--" : formatAge(now - lastUpdatedAt);

  return (
    <>
      <DisclosureBanner />

      <header className="h-14 border-b border-border bg-panel px-4 flex items-center justify-between gap-3">
        {/* Left: logo */}
        <div className="flex items-center gap-3 min-w-[220px]">
          <button
            type="button"
            className="md:hidden h-9 w-9 rounded border border-border flex items-center justify-center"
            onClick={onOpenMobile}
            aria-label="Open menu"
          >
            ☰
          </button>

          <div className="flex items-center gap-2">
            <BrandMark />
            <div className="leading-tight">
              <div className="text-xs text-muted-foreground tracking-[0.12em]">APTER</div>
              <div className="text-[12px] font-semibold tracking-tight">Control Panel</div>
            </div>
          </div>
        </div>

        {/* Center: MARKET REGIME indicator */}
        <div className="hidden sm:flex flex-col items-center justify-center min-w-0">
          <div className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            MARKET REGIME
          </div>
          <div className="mt-0.5">
            <span className={regimeChipClass(data.regime)}>
              <span className="font-semibold tracking-[0.08em]">{data.regime}</span>
            </span>
          </div>
        </div>

        {/* Right: timestamp, freshness, tier */}
        <div className="flex items-center gap-2 justify-end min-w-[260px]">
          <div className="hidden md:flex flex-col items-end leading-tight">
            <div className="text-[11px] text-muted-foreground">System Timestamp</div>
            <div className="font-mono text-[12px]" suppressHydrationWarning>
              {timestamp}
            </div>
          </div>

          <div className="bt-chip border-border text-foreground">
            <span className="text-muted-foreground">Freshness</span>
            <span className="font-mono text-[12px]" suppressHydrationWarning>
              {age}
            </span>
          </div>

          <div className="bt-chip border-border text-foreground">
            <span className="text-muted-foreground">Tier</span>
            <span className="font-semibold">{data.tier}</span>
          </div>

          {error ? (
            <div className="bt-chip bt-chip-off">
              <span className="text-muted-foreground">Data</span>
              <span className="font-semibold">Degraded</span>
            </div>
          ) : (
            <div className="bt-chip bt-chip-neutral">
              <span className="text-muted-foreground">Data</span>
              <span className="font-semibold">{source === "api" ? "Live" : "Local"}</span>
            </div>
          )}
        </div>
      </header>
    </>
  );
}
