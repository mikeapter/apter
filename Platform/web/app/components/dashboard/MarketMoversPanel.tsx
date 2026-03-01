"use client";

import { TrendingUp, TrendingDown } from "lucide-react";
import { sampleGainers, sampleLosers } from "../../lib/dashboard";
import MarketMoverRow from "../market/MarketMoverRow";

export function MarketMoversPanel() {
  return (
    <section className="bt-panel p-4 h-full flex flex-col">
      <div className="bt-panel-title mb-3">MARKET MOVERS</div>

      <div className="flex-1 overflow-auto space-y-4">
        {/* Gainers */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <TrendingUp size={12} className="text-risk-on" />
            <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-medium">
              Top Gainers
            </span>
          </div>
          <div className="space-y-0.5">
            {sampleGainers.map((m) => (
              <MarketMoverRow
                key={m.ticker}
                symbol={m.ticker}
                name={m.companyName}
                grade={m.grade}
              />
            ))}
          </div>
        </div>

        {/* Losers */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <TrendingDown size={12} className="text-risk-off" />
            <span className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground font-medium">
              Top Losers
            </span>
          </div>
          <div className="space-y-0.5">
            {sampleLosers.map((m) => (
              <MarketMoverRow
                key={m.ticker}
                symbol={m.ticker}
                name={m.companyName}
                grade={m.grade}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
