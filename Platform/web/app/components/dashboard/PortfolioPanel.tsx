"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus, X, Briefcase } from "lucide-react";
import { usePortfolio } from "../../providers/PortfolioProvider";
import { GradeBadge } from "../ui/GradeBadge";

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
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

export function PortfolioPanel() {
  const { holdings, totalValue, totalPL, totalPLPct, addHolding, removeHolding } = usePortfolio();
  const [showForm, setShowForm] = useState(false);
  const [ticker, setTicker] = useState("");
  const [shares, setShares] = useState("");
  const [price, setPrice] = useState("");

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const t = ticker.trim().toUpperCase();
    const s = parseFloat(shares);
    const p = parseFloat(price);
    if (!t || isNaN(s) || isNaN(p) || s <= 0 || p <= 0) return;
    addHolding(t, s, p);
    setTicker("");
    setShares("");
    setPrice("");
    setShowForm(false);
  }

  return (
    <section className="bt-panel p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="bt-panel-title">PORTFOLIO</div>
        <button
          type="button"
          onClick={() => setShowForm(!showForm)}
          className="h-7 px-2 rounded border border-border flex items-center gap-1 text-xs hover:bg-muted"
        >
          <Plus size={12} />
          Add
        </button>
      </div>

      {/* Summary */}
      {holdings.length > 0 && (
        <div className="flex items-center gap-4 mb-3 text-sm">
          <div>
            <span className="text-muted-foreground">Value: </span>
            <span className="font-semibold font-mono">{formatCurrency(totalValue)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">P/L: </span>
            <span className={`font-semibold font-mono ${plColor(totalPL)}`}>
              {formatCurrency(totalPL)} ({formatPct(totalPLPct)})
            </span>
          </div>
        </div>
      )}

      {/* Add form */}
      {showForm && (
        <form onSubmit={handleAdd} className="mb-3 p-3 rounded border border-border bg-panel-2 space-y-2">
          <input
            className="bt-input h-8 text-xs"
            placeholder="Ticker (e.g., AAPL)"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
          />
          <div className="flex gap-2">
            <input
              className="bt-input h-8 text-xs flex-1"
              placeholder="Shares"
              type="number"
              step="any"
              min="0.01"
              value={shares}
              onChange={(e) => setShares(e.target.value)}
            />
            <input
              className="bt-input h-8 text-xs flex-1"
              placeholder="Purchase Price"
              type="number"
              step="any"
              min="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="bt-button h-8 text-xs flex-1">
              Add Holding
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="bt-button h-8 text-xs">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Holdings table */}
      <div className="flex-1 overflow-auto">
        {holdings.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground text-sm">
            <Briefcase size={32} className="mb-3 opacity-40" />
            <p>Add your first holding to track performance</p>
          </div>
        ) : (
          <div className="overflow-auto border border-border rounded-md">
            <table className="w-full text-sm">
              <thead className="bg-panel-2">
                <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  <th className="text-left px-2 py-1.5 font-medium">Ticker</th>
                  <th className="text-right px-2 py-1.5 font-medium">Price</th>
                  <th className="text-right px-2 py-1.5 font-medium">P/L</th>
                  <th className="text-center px-2 py-1.5 font-medium">Grade</th>
                  <th className="text-center px-2 py-1.5 font-medium w-8"></th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => (
                  <tr key={h.id} className="border-t border-border">
                    <td className="px-2 py-1.5">
                      <Link href={`/stocks/${h.ticker}`} className="font-mono text-[12px] font-semibold hover:underline">
                        {h.ticker}
                      </Link>
                      <div className="text-[10px] text-muted-foreground">
                        {h.shares} @ {formatCurrency(h.purchasePrice)}
                      </div>
                    </td>
                    <td className="text-right px-2 py-1.5 font-mono text-[12px]">
                      {formatCurrency(h.currentPrice)}
                    </td>
                    <td className={`text-right px-2 py-1.5 font-mono text-[12px] ${plColor(h.unrealizedPL)}`}>
                      {formatPct(h.unrealizedPLPct)}
                    </td>
                    <td className="text-center px-2 py-1.5">
                      <GradeBadge grade={h.grade} />
                    </td>
                    <td className="text-center px-2 py-1.5">
                      <button
                        type="button"
                        onClick={() => removeHolding(h.id)}
                        className="text-muted-foreground hover:text-risk-off"
                        title="Remove holding"
                      >
                        <X size={12} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
