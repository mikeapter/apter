"use client";

import { useState } from "react";
import { AIOverviewCard } from "../../../components/ai/AIOverviewCard";
import { COMPLIANCE } from "../../../lib/compliance";

const POPULAR_TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM"];

export default function AIOverviewPage() {
  const [selectedTickers, setSelectedTickers] = useState<string[]>([]);
  const [timeframe, setTimeframe] = useState<"daily" | "weekly">("daily");
  const [tickerInput, setTickerInput] = useState("");

  function addTicker(t: string) {
    const upper = t.trim().toUpperCase();
    if (upper && !selectedTickers.includes(upper)) {
      setSelectedTickers((prev) => [...prev, upper]);
    }
    setTickerInput("");
  }

  function removeTicker(t: string) {
    setSelectedTickers((prev) => prev.filter((x) => x !== t));
  }

  return (
    <div className="space-y-4 max-w-3xl">
      {/* Page header */}
      <div>
        <h1 className="text-lg font-semibold">AI Market Overview</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          AI-generated market briefing with educational context and risk observations.
        </p>
      </div>

      {/* Disclaimer banner */}
      <div className="rounded-md border border-blue-500/20 bg-blue-500/5 px-3 py-2">
        <p className="text-xs text-blue-400">{COMPLIANCE.DISCLOSURE_BANNER}</p>
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Timeframe toggle */}
        <div className="flex items-center gap-1 bg-panel border border-border rounded-md p-0.5">
          {(["daily", "weekly"] as const).map((tf) => (
            <button
              key={tf}
              type="button"
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                timeframe === tf
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tf.charAt(0).toUpperCase() + tf.slice(1)}
            </button>
          ))}
        </div>

        {/* Ticker input */}
        <div className="flex items-center gap-2 flex-1">
          <input
            type="text"
            value={tickerInput}
            onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addTicker(tickerInput);
              }
            }}
            placeholder="Add ticker..."
            className="h-8 rounded-md border border-border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring/40 w-28"
          />
          <div className="flex flex-wrap gap-1">
            {POPULAR_TICKERS.filter((t) => !selectedTickers.includes(t))
              .slice(0, 4)
              .map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => addTicker(t)}
                  className="text-[10px] text-muted-foreground hover:text-foreground border border-border rounded px-1.5 py-0.5 font-mono"
                >
                  +{t}
                </button>
              ))}
          </div>
        </div>
      </div>

      {/* Selected tickers */}
      {selectedTickers.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Focus:</span>
          {selectedTickers.map((t) => (
            <span
              key={t}
              className="text-xs bg-panel border border-border rounded px-2 py-0.5 font-mono flex items-center gap-1"
            >
              {t}
              <button
                type="button"
                onClick={() => removeTicker(t)}
                className="text-muted-foreground hover:text-foreground text-[10px]"
              >
                x
              </button>
            </span>
          ))}
          <button
            type="button"
            onClick={() => setSelectedTickers([])}
            className="text-[10px] text-muted-foreground hover:text-foreground"
          >
            Clear all
          </button>
        </div>
      )}

      {/* Overview card */}
      <AIOverviewCard
        tickers={selectedTickers.length > 0 ? selectedTickers : undefined}
        timeframe={timeframe}
      />
    </div>
  );
}
