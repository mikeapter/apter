"use client";

import Link from "next/link";
import { X, ArrowUpDown } from "lucide-react";
import { useState, useMemo } from "react";
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

type SortKey = "ticker" | "marketValue" | "unrealizedPL" | "unrealizedPLPct" | "weightPct";
type SortDir = "asc" | "desc";

type Props = {
  holdings: EnrichedHoldingSummary[];
  onRemoveHolding: (ticker: string) => void;
};

export function HoldingsTable({ holdings, onRemoveHolding }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("weightPct");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = useMemo(() => {
    return [...holdings].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc"
          ? av.localeCompare(bv)
          : bv.localeCompare(av);
      }
      const na = typeof av === "number" ? av : 0;
      const nb = typeof bv === "number" ? bv : 0;
      return sortDir === "asc" ? na - nb : nb - na;
    });
  }, [holdings, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  function SortHeader({
    label,
    field,
    align = "right",
  }: {
    label: string;
    field: SortKey;
    align?: "left" | "right";
  }) {
    return (
      <th
        className={`text-${align} px-4 py-2.5 font-medium cursor-pointer select-none hover:text-foreground`}
        onClick={() => toggleSort(field)}
      >
        <span className="inline-flex items-center gap-1">
          {label}
          {sortKey === field && (
            <ArrowUpDown size={10} className="opacity-60" />
          )}
        </span>
      </th>
    );
  }

  return (
    <div className="bt-panel overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-panel-2">
            <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              <SortHeader label="Ticker" field="ticker" align="left" />
              <th className="hidden sm:table-cell text-left px-4 py-2.5 font-medium">Sector</th>
              <th className="hidden sm:table-cell text-right px-4 py-2.5 font-medium">Shares</th>
              <th className="hidden sm:table-cell text-right px-4 py-2.5 font-medium">Avg Cost</th>
              <th className="hidden lg:table-cell text-right px-4 py-2.5 font-medium">Price</th>
              <SortHeader label="Value" field="marketValue" />
              <SortHeader label="P/L ($)" field="unrealizedPL" />
              <SortHeader label="P/L (%)" field="unrealizedPLPct" />
              <SortHeader label="Weight %" field="weightPct" />
              <th className="text-center px-2 py-2.5 font-medium w-8" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((h) => (
              <tr
                key={h.ticker}
                className="border-t border-border hover:bg-muted/30"
              >
                <td className="px-3 py-2.5 sm:px-4">
                  <Link
                    href={`/stocks/${h.ticker}`}
                    className="font-mono font-semibold hover:underline"
                  >
                    {h.ticker}
                  </Link>
                  <div className="text-[10px] text-muted-foreground truncate max-w-[120px]">
                    {h.name}
                  </div>
                </td>
                <td className="hidden sm:table-cell px-4 py-2.5 text-xs text-muted-foreground">
                  {h.sector}
                </td>
                <td className="hidden sm:table-cell text-right px-4 py-2.5 font-mono">
                  {h.shares}
                </td>
                <td className="hidden sm:table-cell text-right px-4 py-2.5 font-mono">
                  {formatCurrency(h.avgCost)}
                </td>
                <td className="hidden lg:table-cell text-right px-4 py-2.5 font-mono">
                  {formatCurrency(h.price)}
                </td>
                <td className="text-right px-3 py-2.5 sm:px-4 font-mono">
                  {formatCurrency(h.marketValue)}
                </td>
                <td
                  className={`text-right px-3 py-2.5 sm:px-4 font-mono ${plColor(h.unrealizedPL)}`}
                >
                  {formatCurrency(h.unrealizedPL)}
                </td>
                <td
                  className={`text-right px-3 py-2.5 sm:px-4 font-mono ${plColor(h.unrealizedPLPct)}`}
                >
                  {formatPct(h.unrealizedPLPct)}
                </td>
                <td className="text-right px-3 py-2.5 sm:px-4 font-mono text-muted-foreground">
                  {h.weightPct.toFixed(1)}%
                </td>
                <td className="text-center px-2 py-2.5">
                  <button
                    type="button"
                    onClick={() => onRemoveHolding(h.ticker)}
                    className="text-muted-foreground hover:text-risk-off"
                    title="Remove holding"
                  >
                    <X size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
