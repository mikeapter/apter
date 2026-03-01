"use client";

import React from "react";
import { useLiveQuote, formatUsd } from "../../hooks/useLiveQuote";

export default function ScreenerPriceCell({ symbol }: { symbol: string }) {
  const { quote, isLoading } = useLiveQuote(symbol, { refreshMs: 20000 });

  return (
    <span className="tabular-nums font-mono">
      {isLoading ? "—" : formatUsd(quote?.price)}
    </span>
  );
}
