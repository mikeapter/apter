"use client";

import Link from "next/link";
import { TrendingUp, TrendingDown } from "lucide-react";
import { sampleGainers, sampleLosers, type MarketMover } from "../../lib/dashboard";
import { GradeBadge } from "../ui/GradeBadge";

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

function MoverRow({ m }: { m: MarketMover }) {
  const isPositive = m.change >= 0;
  const color = isPositive ? "text-risk-on" : "text-risk-off";
  const sign = isPositive ? "+" : "";

  return (
    <Link
      href={`/stocks/${m.ticker}`}
      className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-muted/60 group"
    >
      <div className="min-w-0">
        <div className="font-mono text-[12px] font-semibold group-hover:underline">{m.ticker}</div>
        <div className="text-[10px] text-muted-foreground truncate">{m.companyName}</div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <div className="text-right">
          <div className="font-mono text-[12px]">{formatCurrency(m.price)}</div>
          <div className={`font-mono text-[10px] ${color}`}>
            {sign}{m.changePct.toFixed(2)}%
          </div>
        </div>
        <GradeBadge grade={m.grade} />
      </div>
    </Link>
  );
}

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
              <MoverRow key={m.ticker} m={m} />
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
              <MoverRow key={m.ticker} m={m} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
