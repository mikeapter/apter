"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { Plus, X, Eye } from "lucide-react";
import { getMockPrice, getMockGrade } from "../../lib/stockData";
import { GradeBadge } from "../../components/ui/GradeBadge";

const LS_KEY = "apter_watchlist";

type WatchlistItem = {
  ticker: string;
  addedAt: string;
};

type EnrichedItem = WatchlistItem & {
  price: number;
  change: number;
  changePct: number;
  grade: number;
};

function loadWatchlist(): WatchlistItem[] {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveWatchlist(items: WatchlistItem[]) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(items));
  } catch {}
}

function enrichItem(item: WatchlistItem): EnrichedItem {
  const price = getMockPrice(item.ticker);
  const grade = getMockGrade(item.ticker);
  let hash = 0;
  for (let i = 0; i < item.ticker.length; i++) hash = ((hash << 5) - hash + item.ticker.charCodeAt(i)) | 0;
  const changePct = ((hash % 800) - 400) / 100;
  const change = price * (changePct / 100);
  return { ...item, price, change, changePct, grade };
}

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [ticker, setTicker] = useState("");

  useEffect(() => {
    setItems(loadWatchlist());
  }, []);

  const persist = useCallback((next: WatchlistItem[]) => {
    setItems(next);
    saveWatchlist(next);
  }, []);

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const t = ticker.trim().toUpperCase();
    if (!t) return;
    if (items.some((i) => i.ticker === t)) return;
    persist([...items, { ticker: t, addedAt: new Date().toISOString() }]);
    setTicker("");
  }

  function handleRemove(t: string) {
    persist(items.filter((i) => i.ticker !== t));
  }

  const enriched = items.map(enrichItem);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Watchlist</div>
        <div className="text-muted-foreground text-sm">Track tickers you are monitoring.</div>
      </div>

      <form onSubmit={handleAdd} className="flex gap-2">
        <input
          className="bt-input max-w-xs"
          placeholder="Add ticker (e.g., AAPL)"
          value={ticker}
          onChange={(e) => setTicker(e.target.value)}
        />
        <button type="submit" className="bt-button h-10 gap-2">
          <Plus size={14} />
          Add
        </button>
      </form>

      {enriched.length === 0 ? (
        <div className="bt-panel p-12 flex flex-col items-center justify-center text-muted-foreground">
          <Eye size={40} className="mb-4 opacity-40" />
          <p className="text-sm">Your watchlist is empty. Add tickers to start monitoring.</p>
        </div>
      ) : (
        <div className="bt-panel">
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-panel-2">
                <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  <th className="text-left px-4 py-2.5 font-medium">Ticker</th>
                  <th className="text-right px-4 py-2.5 font-medium">Price</th>
                  <th className="text-right px-4 py-2.5 font-medium">Change</th>
                  <th className="text-right px-4 py-2.5 font-medium">Change %</th>
                  <th className="text-center px-4 py-2.5 font-medium">Grade</th>
                  <th className="text-center px-4 py-2.5 font-medium w-10"></th>
                </tr>
              </thead>
              <tbody>
                {enriched.map((item) => {
                  const color = item.changePct >= 0 ? "text-risk-on" : "text-risk-off";
                  const sign = item.changePct >= 0 ? "+" : "";
                  return (
                    <tr key={item.ticker} className="border-t border-border hover:bg-muted/30">
                      <td className="px-4 py-2.5">
                        <Link href={`/stocks/${item.ticker}`} className="font-mono font-semibold hover:underline">
                          {item.ticker}
                        </Link>
                      </td>
                      <td className="text-right px-4 py-2.5 font-mono">{formatCurrency(item.price)}</td>
                      <td className={`text-right px-4 py-2.5 font-mono ${color}`}>
                        {sign}{formatCurrency(item.change)}
                      </td>
                      <td className={`text-right px-4 py-2.5 font-mono ${color}`}>
                        {sign}{item.changePct.toFixed(2)}%
                      </td>
                      <td className="text-center px-4 py-2.5">
                        <GradeBadge grade={item.grade} />
                      </td>
                      <td className="text-center px-4 py-2.5">
                        <button
                          type="button"
                          onClick={() => handleRemove(item.ticker)}
                          className="text-muted-foreground hover:text-risk-off"
                          title="Remove from watchlist"
                        >
                          <X size={14} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
