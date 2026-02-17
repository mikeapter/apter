"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { getMockPrice, getMockGrade } from "../../lib/stockData";
import { GradeBadge } from "../../components/ui/GradeBadge";
import { COMPLIANCE } from "../../lib/compliance";

type ScreenerStock = {
  ticker: string;
  company: string;
  sector: string;
  marketCap: string;
  price: number;
  grade: number;
};

const UNIVERSE: ScreenerStock[] = [
  { ticker: "AAPL", company: "Apple Inc.", sector: "Technology", marketCap: "Large" },
  { ticker: "MSFT", company: "Microsoft Corporation", sector: "Technology", marketCap: "Large" },
  { ticker: "NVDA", company: "NVIDIA Corporation", sector: "Technology", marketCap: "Large" },
  { ticker: "GOOGL", company: "Alphabet Inc.", sector: "Technology", marketCap: "Large" },
  { ticker: "AMZN", company: "Amazon.com Inc.", sector: "Consumer Discretionary", marketCap: "Large" },
  { ticker: "META", company: "Meta Platforms Inc.", sector: "Technology", marketCap: "Large" },
  { ticker: "TSLA", company: "Tesla Inc.", sector: "Consumer Discretionary", marketCap: "Large" },
  { ticker: "JPM", company: "JPMorgan Chase & Co.", sector: "Financials", marketCap: "Large" },
  { ticker: "V", company: "Visa Inc.", sector: "Financials", marketCap: "Large" },
  { ticker: "JNJ", company: "Johnson & Johnson", sector: "Healthcare", marketCap: "Large" },
  { ticker: "UNH", company: "UnitedHealth Group", sector: "Healthcare", marketCap: "Large" },
  { ticker: "XOM", company: "Exxon Mobil Corp.", sector: "Energy", marketCap: "Large" },
  { ticker: "PG", company: "Procter & Gamble", sector: "Consumer Staples", marketCap: "Large" },
  { ticker: "HD", company: "Home Depot Inc.", sector: "Consumer Discretionary", marketCap: "Large" },
  { ticker: "LLY", company: "Eli Lilly & Co.", sector: "Healthcare", marketCap: "Large" },
].map((s) => ({
  ...s,
  price: getMockPrice(s.ticker),
  grade: getMockGrade(s.ticker),
}));

const SECTORS = ["All", ...Array.from(new Set(UNIVERSE.map((s) => s.sector))).sort()];
const SORT_OPTIONS = [
  { label: "Grade (High to Low)", value: "grade-desc" },
  { label: "Grade (Low to High)", value: "grade-asc" },
  { label: "Price (High to Low)", value: "price-desc" },
  { label: "Price (Low to High)", value: "price-asc" },
  { label: "Ticker (A-Z)", value: "ticker-asc" },
];

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });
}

export default function ScreenerPage() {
  const [sector, setSector] = useState("All");
  const [minGrade, setMinGrade] = useState(1);
  const [sort, setSort] = useState("grade-desc");
  const [query, setQuery] = useState("");

  const results = useMemo(() => {
    let filtered = UNIVERSE.filter((s) => {
      if (sector !== "All" && s.sector !== sector) return false;
      if (s.grade < minGrade) return false;
      if (query) {
        const q = query.toLowerCase();
        if (!s.ticker.toLowerCase().includes(q) && !s.company.toLowerCase().includes(q)) return false;
      }
      return true;
    });

    const [field, dir] = sort.split("-");
    filtered.sort((a, b) => {
      let cmp = 0;
      if (field === "grade") cmp = a.grade - b.grade;
      else if (field === "price") cmp = a.price - b.price;
      else cmp = a.ticker.localeCompare(b.ticker);
      return dir === "desc" ? -cmp : cmp;
    });

    return filtered;
  }, [sector, minGrade, sort, query]);

  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Screener</div>
        <div className="text-muted-foreground text-sm">Filter and sort stocks by sector, grade, and more.</div>
      </div>

      {/* Filters */}
      <div className="bt-panel p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground block mb-1">Search</label>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                className="bt-input pl-9"
                placeholder="Ticker or company..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground block mb-1">Sector</label>
            <select
              className="bt-input"
              value={sector}
              onChange={(e) => setSector(e.target.value)}
            >
              {SECTORS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground block mb-1">
              Min Grade ({minGrade})
            </label>
            <input
              type="range"
              min={1}
              max={10}
              value={minGrade}
              onChange={(e) => setMinGrade(parseInt(e.target.value))}
              className="w-full accent-[hsl(var(--risk-on))]"
            />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground block mb-1">Sort By</label>
            <select
              className="bt-input"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              {SORT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="bt-panel">
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-panel-2">
              <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                <th className="text-left px-4 py-2.5 font-medium">Ticker</th>
                <th className="text-left px-4 py-2.5 font-medium">Company</th>
                <th className="text-left px-4 py-2.5 font-medium">Sector</th>
                <th className="text-right px-4 py-2.5 font-medium">Price</th>
                <th className="text-center px-4 py-2.5 font-medium">Grade</th>
              </tr>
            </thead>
            <tbody>
              {results.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground text-sm">
                    No stocks match the current filters.
                  </td>
                </tr>
              ) : (
                results.map((s) => (
                  <tr key={s.ticker} className="border-t border-border hover:bg-muted/30">
                    <td className="px-4 py-2.5">
                      <Link href={`/stocks/${s.ticker}`} className="font-mono font-semibold hover:underline">
                        {s.ticker}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground">{s.company}</td>
                    <td className="px-4 py-2.5 text-muted-foreground">{s.sector}</td>
                    <td className="text-right px-4 py-2.5 font-mono">{formatCurrency(s.price)}</td>
                    <td className="text-center px-4 py-2.5">
                      <GradeBadge grade={s.grade} />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="text-xs text-muted-foreground">
        {COMPLIANCE.NOT_INVESTMENT_ADVICE}
      </div>
    </div>
  );
}
