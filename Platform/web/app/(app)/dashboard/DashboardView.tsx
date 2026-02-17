"use client";

import { PortfolioPanel } from "../../components/dashboard/PortfolioPanel";
import { PerformancePanel } from "../../components/dashboard/PerformancePanel";
import { MarketMoversPanel } from "../../components/dashboard/MarketMoversPanel";
import { PortfolioProvider } from "../../providers/PortfolioProvider";

export default function DashboardView() {
  return (
    <PortfolioProvider>
      <div className="h-full">
        <div className="grid gap-3 lg:grid-cols-12 h-full min-h-[500px]">
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
      </div>
    </PortfolioProvider>
  );
}
