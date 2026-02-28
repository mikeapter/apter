"use client";

import { PortfolioPanel } from "../../components/dashboard/PortfolioPanel";
import { PerformancePanel } from "../../components/dashboard/PerformancePanel";
import { MarketMoversPanel } from "../../components/dashboard/MarketMoversPanel";
import { MarketBriefPanel } from "../../components/dashboard/MarketBriefPanel";
import { PortfolioProvider } from "../../providers/PortfolioProvider";
import { StartHerePanel, useIsEmptyAccount } from "../../components/dashboard/StartHerePanel";

function DashboardContent() {
  const showOnboarding = useIsEmptyAccount();

  return (
    <div className="h-full space-y-3">
      {showOnboarding && <StartHerePanel />}

      <div className="grid gap-3 lg:grid-cols-12 min-h-[500px]">
        {/* Left: Portfolio */}
        <div className="lg:col-span-3">
          <PortfolioPanel />
        </div>

        {/* Center: Performance chart */}
        <div className="lg:col-span-6">
          <PerformancePanel />
        </div>

        {/* Right: Market Movers */}
        <div className="lg:col-span-3">
          <MarketMoversPanel />
        </div>
      </div>

      {/* Market Intelligence Brief (deterministic, no LLM) */}
      <MarketBriefPanel />
    </div>
  );
}

export default function DashboardView() {
  return (
    <PortfolioProvider>
      <DashboardContent />
    </PortfolioProvider>
  );
}
