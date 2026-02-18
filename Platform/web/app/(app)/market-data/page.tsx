"use client";

import Link from "next/link";

type IndexData = {
  name: string;
  ticker: string;
  value: number;
  change: number;
  changePct: number;
};

type SectorData = {
  name: string;
  changePct: number;
};

type EarningsEvent = {
  ticker: string;
  company: string;
  date: string;
  estimate: string;
};

const INDICES: IndexData[] = [
  { name: "S&P 500", ticker: "SPY", value: 5123.41, change: 24.56, changePct: 0.48 },
  { name: "Nasdaq Composite", ticker: "QQQ", value: 16245.78, change: 112.34, changePct: 0.70 },
  { name: "Dow Jones", ticker: "DIA", value: 38876.23, change: 145.67, changePct: 0.38 },
  { name: "Russell 2000", ticker: "IWM", value: 2034.56, change: -8.23, changePct: -0.40 },
];

const SECTORS: SectorData[] = [
  { name: "Technology", changePct: 1.24 },
  { name: "Financials", changePct: 0.89 },
  { name: "Healthcare", changePct: 0.45 },
  { name: "Consumer Discretionary", changePct: 0.32 },
  { name: "Industrials", changePct: 0.18 },
  { name: "Communication Services", changePct: -0.12 },
  { name: "Consumer Staples", changePct: -0.28 },
  { name: "Real Estate", changePct: -0.45 },
  { name: "Materials", changePct: -0.52 },
  { name: "Utilities", changePct: -0.67 },
  { name: "Energy", changePct: -1.15 },
];

const EARNINGS: EarningsEvent[] = [
  { ticker: "NVDA", company: "NVIDIA", date: "2026-02-26", estimate: "$0.89 EPS" },
  { ticker: "CRM", company: "Salesforce", date: "2026-02-27", estimate: "$2.45 EPS" },
  { ticker: "COST", company: "Costco", date: "2026-03-04", estimate: "$3.78 EPS" },
  { ticker: "AVGO", company: "Broadcom", date: "2026-03-06", estimate: "$1.42 EPS" },
  { ticker: "ORCL", company: "Oracle", date: "2026-03-10", estimate: "$1.65 EPS" },
  { ticker: "ADBE", company: "Adobe", date: "2026-03-12", estimate: "$4.75 EPS" },
];

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function sectorBarColor(pct: number): string {
  if (pct > 0.5) return "bg-risk-on";
  if (pct > 0) return "bg-risk-on/60";
  if (pct > -0.5) return "bg-risk-off/60";
  return "bg-risk-off";
}

export default function MarketDataPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Market Data</div>
        <div className="text-muted-foreground text-sm">Major indices, sector performance, and upcoming earnings.</div>
      </div>

      {/* Major Indices */}
      <section>
        <div className="bt-panel-title mb-3">MAJOR INDICES</div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {INDICES.map((idx) => {
            const color = idx.changePct >= 0 ? "text-risk-on" : "text-risk-off";
            const sign = idx.changePct >= 0 ? "+" : "";
            return (
              <Link key={idx.ticker} href={`/stocks/${idx.ticker}`} className="bt-panel p-4 hover:bg-muted/30 transition-colors">
                <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{idx.name}</div>
                <div className="mt-1 text-xl font-semibold font-mono">{formatCurrency(idx.value)}</div>
                <div className={`mt-0.5 text-sm font-mono ${color}`}>
                  {sign}{formatCurrency(idx.change)} ({sign}{idx.changePct.toFixed(2)}%)
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Sector Performance */}
        <section className="bt-panel p-4">
          <div className="bt-panel-title mb-3">SECTOR PERFORMANCE (TODAY)</div>
          <div className="space-y-2">
            {SECTORS.map((s) => {
              const color = s.changePct >= 0 ? "text-risk-on" : "text-risk-off";
              const sign = s.changePct >= 0 ? "+" : "";
              const barWidth = Math.min(100, Math.abs(s.changePct) * 40);
              return (
                <div key={s.name} className="flex items-center gap-3">
                  <div className="w-44 text-sm truncate">{s.name}</div>
                  <div className="flex-1 h-4 bg-panel-2 rounded-sm overflow-hidden relative">
                    <div
                      className={`h-full rounded-sm ${sectorBarColor(s.changePct)}`}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                  <div className={`w-16 text-right text-sm font-mono ${color}`}>
                    {sign}{s.changePct.toFixed(2)}%
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Earnings Calendar */}
        <section className="bt-panel p-4">
          <div className="bt-panel-title mb-3">UPCOMING EARNINGS</div>
          <div className="overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-panel-2">
                <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  <th className="text-left px-3 py-2 font-medium">Ticker</th>
                  <th className="text-left px-3 py-2 font-medium">Company</th>
                  <th className="text-left px-3 py-2 font-medium">Date</th>
                  <th className="text-left px-3 py-2 font-medium">Est.</th>
                </tr>
              </thead>
              <tbody>
                {EARNINGS.map((e) => (
                  <tr key={e.ticker} className="border-t border-border">
                    <td className="px-3 py-2">
                      <Link href={`/stocks/${e.ticker}`} className="font-mono font-semibold hover:underline">
                        {e.ticker}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">{e.company}</td>
                    <td className="px-3 py-2 font-mono text-[12px] text-muted-foreground">{e.date}</td>
                    <td className="px-3 py-2 font-mono text-[12px]">{e.estimate}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
