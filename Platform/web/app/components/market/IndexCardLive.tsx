"use client";

import React from "react";
import Link from "next/link";
import { useLiveQuote } from "../../hooks/useLiveQuote";

type Props = {
  title: string;
  symbol: string;
};

function formatNumber(v: number | null | undefined) {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  return v.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatChange(v: number | null | undefined) {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPct(v: number | null | undefined) {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

export default function IndexCardLive({ title, symbol }: Props) {
  const { quote, isLoading } = useLiveQuote(symbol, { refreshMs: 20000 });

  const changePct = quote?.changePct;
  const isPositive =
    !isLoading &&
    changePct !== null &&
    changePct !== undefined &&
    changePct >= 0;
  const color = isLoading
    ? ""
    : isPositive
      ? "text-risk-on"
      : "text-risk-off";
  const sign = isPositive ? "+" : "";

  return (
    <Link
      href={`/stocks/${symbol}`}
      className="bt-panel p-4 hover:bg-muted/30 transition-colors"
    >
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
        {title}
      </div>
      <div className="mt-1 text-xl font-semibold font-mono tabular-nums">
        {isLoading ? "—" : formatNumber(quote?.price)}
      </div>
      <div className={`mt-0.5 text-sm font-mono tabular-nums ${color}`}>
        {isLoading
          ? "—"
          : `${formatChange(quote?.change)} (${formatPct(quote?.changePct)})`}
      </div>
    </Link>
  );
}
