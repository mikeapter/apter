"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus, X, Briefcase } from "lucide-react";
import { PortfolioProvider, usePortfolio } from "../../providers/PortfolioProvider";
import { GradeBadge } from "../../components/ui/GradeBadge";
import { COMPLIANCE } from "../../lib/compliance";

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

function PortfolioContent() {
  const { holdings, totalValue, totalCost, totalPL, totalPLPct, addHolding, removeHolding } = usePortfolio();
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-2xl font-semibold">Portfolio</div>
          <div className="text-muted-foreground text-sm">Track your holdings, cost basis, and unrealized performance.</div>
        </div>
        <button
          type="button"
          onClick={() => setShowForm(!showForm)}
          className="bt-button h-10 gap-2"
        >
          <Plus size={14} />
          Add Holding
        </button>
      </div>

      {/* Summary cards */}
      {holdings.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-4">
          <div className="bt-panel p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Total Value</div>
            <div className="mt-1 text-xl font-semibold font-mono">{formatCurrency(totalValue)}</div>
          </div>
          <div className="bt-panel p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Total Cost</div>
            <div className="mt-1 text-xl font-semibold font-mono">{formatCurrency(totalCost)}</div>
          </div>
          <div className="bt-panel p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Unrealized P/L</div>
            <div className={`mt-1 text-xl font-semibold font-mono ${plColor(totalPL)}`}>
              {formatCurrency(totalPL)}
            </div>
          </div>
          <div className="bt-panel p-4">
            <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Return</div>
            <div className={`mt-1 text-xl font-semibold font-mono ${plColor(totalPLPct)}`}>
              {formatPct(totalPLPct)}
            </div>
          </div>
        </div>
      )}

      {/* Add form */}
      {showForm && (
        <form onSubmit={handleAdd} className="bt-panel p-4 space-y-3">
          <div className="font-semibold text-sm">Add New Holding</div>
          <div className="grid gap-3 sm:grid-cols-3">
            <input
              className="bt-input"
              placeholder="Ticker (e.g., AAPL)"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
            />
            <input
              className="bt-input"
              placeholder="Shares"
              type="number"
              step="any"
              min="0.01"
              value={shares}
              onChange={(e) => setShares(e.target.value)}
            />
            <input
              className="bt-input"
              placeholder="Purchase Price ($)"
              type="number"
              step="any"
              min="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
            />
          </div>
          <div className="flex gap-2">
            <button type="submit" className="bt-button h-10 px-6">
              Add
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="bt-button h-10 px-4">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Holdings table */}
      {holdings.length === 0 ? (
        <div className="bt-panel p-12 flex flex-col items-center justify-center text-muted-foreground">
          <Briefcase size={40} className="mb-4 opacity-40" />
          <p className="text-sm">No holdings yet. Add your first position to begin tracking.</p>
        </div>
      ) : (
        <div className="bt-panel">
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-panel-2">
                <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  <th className="text-left px-4 py-2.5 font-medium">Ticker</th>
                  <th className="text-right px-4 py-2.5 font-medium">Shares</th>
                  <th className="text-right px-4 py-2.5 font-medium">Avg Cost</th>
                  <th className="text-right px-4 py-2.5 font-medium">Price</th>
                  <th className="text-right px-4 py-2.5 font-medium">Value</th>
                  <th className="text-right px-4 py-2.5 font-medium">Cost Basis</th>
                  <th className="text-right px-4 py-2.5 font-medium">P/L ($)</th>
                  <th className="text-right px-4 py-2.5 font-medium">P/L (%)</th>
                  <th className="text-center px-4 py-2.5 font-medium">Grade</th>
                  <th className="text-center px-4 py-2.5 font-medium w-10"></th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => (
                  <tr key={h.id} className="border-t border-border hover:bg-muted/30">
                    <td className="px-4 py-2.5">
                      <Link href={`/stocks/${h.ticker}`} className="font-mono font-semibold hover:underline">
                        {h.ticker}
                      </Link>
                    </td>
                    <td className="text-right px-4 py-2.5 font-mono">{h.shares}</td>
                    <td className="text-right px-4 py-2.5 font-mono">{formatCurrency(h.purchasePrice)}</td>
                    <td className="text-right px-4 py-2.5 font-mono">{formatCurrency(h.currentPrice)}</td>
                    <td className="text-right px-4 py-2.5 font-mono">{formatCurrency(h.positionValue)}</td>
                    <td className="text-right px-4 py-2.5 font-mono">{formatCurrency(h.costBasis)}</td>
                    <td className={`text-right px-4 py-2.5 font-mono ${plColor(h.unrealizedPL)}`}>
                      {formatCurrency(h.unrealizedPL)}
                    </td>
                    <td className={`text-right px-4 py-2.5 font-mono ${plColor(h.unrealizedPLPct)}`}>
                      {formatPct(h.unrealizedPLPct)}
                    </td>
                    <td className="text-center px-4 py-2.5">
                      <GradeBadge grade={h.grade} />
                    </td>
                    <td className="text-center px-4 py-2.5">
                      <button
                        type="button"
                        onClick={() => removeHolding(h.id)}
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
      )}

      <div className="text-xs text-muted-foreground">
        {COMPLIANCE.PORTFOLIO_DISCLAIMER}
      </div>
    </div>
  );
}

export default function PortfolioPage() {
  return (
    <PortfolioProvider>
      <PortfolioContent />
    </PortfolioProvider>
  );
}
