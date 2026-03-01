"use client";

import React from "react";
import Link from "next/link";
import { useLiveQuote, formatUsd } from "../../hooks/useLiveQuote";
import { GradeBadge } from "../ui/GradeBadge";

type Props = {
  symbol: string;
  name?: string;
  grade?: number;
};

export default function MarketMoverRow({ symbol, name, grade }: Props) {
  const { quote, isLoading } = useLiveQuote(symbol, { refreshMs: 15000 });

  const priceText = isLoading ? "—" : formatUsd(quote?.price);
  const changePct = quote?.changePct;
  const isPositive =
    changePct !== null && changePct !== undefined && changePct >= 0;
  const color = isLoading
    ? "text-muted-foreground"
    : isPositive
      ? "text-risk-on"
      : "text-risk-off";
  const sign = isPositive ? "+" : "";
  const changePctText =
    isLoading || changePct === null || changePct === undefined
      ? "—"
      : `${sign}${changePct.toFixed(2)}%`;

  return (
    <Link
      href={`/stocks/${symbol}`}
      className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-muted/60 group"
    >
      <div className="min-w-0">
        <div className="font-mono text-[12px] font-semibold group-hover:underline">
          {symbol}
        </div>
        <div className="text-[10px] text-muted-foreground truncate">
          {name ?? ""}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <div className="text-right">
          <div className="font-mono text-[12px] tabular-nums">{priceText}</div>
          <div className={`font-mono text-[10px] tabular-nums ${color}`}>
            {changePctText}
          </div>
        </div>
        {grade !== undefined && <GradeBadge grade={grade} />}
      </div>
    </Link>
  );
}
