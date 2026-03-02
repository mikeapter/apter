"use client";

import type { PortfolioSummary } from "../../lib/api/portfolio";

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
  totals: PortfolioSummary["totals"];
};

export function PortfolioKpiCards({ totals }: Props) {
  const cards: { label: string; value: string; colorClass?: string }[] = [
    { label: "Market Value", value: formatCurrency(totals.marketValue) },
    { label: "Cost Basis", value: formatCurrency(totals.costBasis) },
    {
      label: "Unrealized P/L",
      value: formatCurrency(totals.unrealizedPL),
      colorClass: plColor(totals.unrealizedPL),
    },
    {
      label: "Return",
      value: formatPct(totals.unrealizedPLPct),
      colorClass: plColor(totals.unrealizedPLPct),
    },
    {
      label: "Day P/L",
      value: formatCurrency(totals.dayPL),
      colorClass: plColor(totals.dayPL),
    },
    {
      label: "Day Change",
      value: formatPct(totals.dayPLPct),
      colorClass: plColor(totals.dayPLPct),
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {cards.map((c) => (
        <div key={c.label} className="bt-panel p-4">
          <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            {c.label}
          </div>
          <div
            className={`mt-1 text-lg font-semibold font-mono ${c.colorClass ?? "text-foreground"}`}
          >
            {c.value}
          </div>
        </div>
      ))}
    </div>
  );
}
