"use client";

import Link from "next/link";
import { X } from "lucide-react";
import type { EnrichedHoldingSummary } from "../../lib/api/portfolio";

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

function formatPct(n: number): string {
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}%`;
}

function plColor(n: number): string {
  if (n > 0) return "text-risk-on";
  if (n < 0) return "text-risk-off";
  return "text-foreground";
}

type Props = {
  sector: string;
  holdings: EnrichedHoldingSummary[];
  onClose: () => void;
};

export function SectorDrilldown({ sector, holdings, onClose }: Props) {
  const sectorHoldings = holdings.filter((h) => h.sector === sector);
  const sectorValue = sectorHoldings.reduce((sum, h) => sum + h.marketValue, 0);
  const sectorPL = sectorHoldings.reduce((sum, h) => sum + h.unrealizedPL, 0);

  return (
    <div className="bt-panel p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="bt-panel-title">{sector}</div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {sectorHoldings.length} holding{sectorHoldings.length !== 1 ? "s" : ""}{" "}
            &middot; {formatCurrency(sectorValue)} &middot;{" "}
            <span className={plColor(sectorPL)}>
              {formatCurrency(sectorPL)} P/L
            </span>
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground p-1"
          title="Close drilldown"
        >
          <X size={16} />
        </button>
      </div>

      <div className="overflow-auto">
        <table className="w-full text-xs">
          <thead className="bg-panel-2">
            <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              <th className="text-left px-3 py-2 font-medium">Ticker</th>
              <th className="text-right px-3 py-2 font-medium">Weight</th>
              <th className="text-right px-3 py-2 font-medium">Price</th>
              <th className="text-right px-3 py-2 font-medium">Value</th>
              <th className="text-right px-3 py-2 font-medium">P/L</th>
              <th className="text-right px-3 py-2 font-medium">P/L %</th>
            </tr>
          </thead>
          <tbody>
            {sectorHoldings.map((h) => (
              <tr
                key={h.ticker}
                className="border-t border-border hover:bg-muted/30"
              >
                <td className="px-3 py-2">
                  <Link
                    href={`/stocks/${h.ticker}`}
                    className="font-mono font-semibold hover:underline"
                  >
                    {h.ticker}
                  </Link>
                  <div className="text-muted-foreground truncate max-w-[140px]">
                    {h.name}
                  </div>
                </td>
                <td className="text-right px-3 py-2 font-mono">
                  {h.weightPct.toFixed(1)}%
                </td>
                <td className="text-right px-3 py-2 font-mono">
                  {formatCurrency(h.price)}
                </td>
                <td className="text-right px-3 py-2 font-mono">
                  {formatCurrency(h.marketValue)}
                </td>
                <td
                  className={`text-right px-3 py-2 font-mono ${plColor(h.unrealizedPL)}`}
                >
                  {formatCurrency(h.unrealizedPL)}
                </td>
                <td
                  className={`text-right px-3 py-2 font-mono ${plColor(h.unrealizedPLPct)}`}
                >
                  {formatPct(h.unrealizedPLPct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
