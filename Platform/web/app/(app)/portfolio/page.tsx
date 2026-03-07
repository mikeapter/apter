"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Plus,
  Briefcase,
  Upload,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  BarChart3,
  PieChart,
  ShieldAlert,
} from "lucide-react";
import { PortfolioProvider, usePortfolio } from "../../providers/PortfolioProvider";
import { COMPLIANCE } from "../../lib/compliance";
import {
  getPortfolioSummary,
  getPortfolioAIBrief,
} from "../../lib/api/portfolio";
import type {
  HoldingInput,
  PortfolioSummary,
  AIBriefResponse,
} from "../../lib/api/portfolio";
import { PortfolioKpiCards } from "../../components/portfolio/PortfolioKpiCards";
import { SectorAllocationPie } from "../../components/portfolio/SectorAllocationPie";
import { SectorDrilldown } from "../../components/portfolio/SectorDrilldown";
import { PortfolioAIBrief } from "../../components/portfolio/PortfolioAIBrief";
import { HoldingsTable } from "../../components/portfolio/HoldingsTable";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatCurrency(n: number): string {
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

// ─── Add Holding Form ────────────────────────────────────────────────────────

function AddHoldingForm({
  onAdd,
  onCancel,
}: {
  onAdd: (ticker: string, shares: number, price: number) => void;
  onCancel: () => void;
}) {
  const [ticker, setTicker] = useState("");
  const [shares, setShares] = useState("");
  const [price, setPrice] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const t = ticker.trim().toUpperCase();
    const s = parseFloat(shares);
    const p = parseFloat(price);
    if (!t || isNaN(s) || isNaN(p) || s <= 0 || p <= 0) return;
    onAdd(t, s, p);
  }

  return (
    <form onSubmit={handleSubmit} className="bt-panel p-4 space-y-3">
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
        <button type="submit" className="bt-button-primary px-6">
          Add
        </button>
        <button type="button" onClick={onCancel} className="bt-button px-4">
          Cancel
        </button>
      </div>
    </form>
  );
}

// ─── Skeleton Performance Preview ────────────────────────────────────────────

function PerformancePreview() {
  const bars = [40, 55, 35, 65, 50, 70, 45, 60, 75, 50, 65, 58];
  return (
    <div className="bt-panel p-4">
      <div className="bt-panel-title mb-3">Performance Preview</div>
      <div className="flex items-end gap-1 h-16">
        {bars.map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm bg-muted-foreground/10"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
      <div className="flex justify-between mt-2">
        <span className="text-[10px] text-muted-foreground/40">1M</span>
        <span className="text-[10px] text-muted-foreground/40">6M</span>
        <span className="text-[10px] text-muted-foreground/40">1Y</span>
      </div>
    </div>
  );
}

// ─── Main Content ────────────────────────────────────────────────────────────

function PortfolioContent() {
  const { holdings, addHolding, removeHolding } = usePortfolio();

  const [showForm, setShowForm] = useState(false);

  // Backend-computed data
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [brief, setBrief] = useState<AIBriefResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [briefLoading, setBriefLoading] = useState(false);
  const [briefError, setBriefError] = useState<string | null>(null);

  // Sector drilldown
  const [selectedSector, setSelectedSector] = useState<string | null>(null);

  // Build a stable key from holdings for dependency tracking
  const holdingsKey = holdings
    .map((h) => `${h.ticker}:${h.shares}:${h.purchasePrice}`)
    .join(",");

  // Convert holdings to API input format
  const toInputs = useCallback((): HoldingInput[] => {
    return holdings.map((h) => ({
      ticker: h.ticker,
      shares: h.shares,
      purchasePrice: h.purchasePrice,
    }));
  }, [holdingsKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch summary from backend when holdings change
  useEffect(() => {
    const inputs = toInputs();
    if (inputs.length === 0) {
      setSummary(null);
      setBrief(null);
      return;
    }

    let cancelled = false;
    setSummaryLoading(true);

    getPortfolioSummary(inputs)
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch(() => {
        /* keep stale summary */
      })
      .finally(() => {
        if (!cancelled) setSummaryLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [toInputs]);

  // Fetch AI brief (separate, slower call)
  useEffect(() => {
    const inputs = toInputs();
    if (inputs.length === 0) {
      setBrief(null);
      return;
    }

    let cancelled = false;
    setBriefLoading(true);
    setBriefError(null);

    getPortfolioAIBrief(inputs)
      .then((data) => {
        if (!cancelled) setBrief(data);
      })
      .catch(() => {
        if (!cancelled) setBriefError("Failed to generate brief");
      })
      .finally(() => {
        if (!cancelled) setBriefLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [toInputs]);

  // ─── Handlers ─────────────────────────────────────────────────────────────

  function handleAddHolding(t: string, s: number, p: number) {
    addHolding(t, s, p);
    setShowForm(false);
  }

  function handleRemoveHolding(tickerToRemove: string) {
    const holding = holdings.find((h) => h.ticker === tickerToRemove);
    if (holding) removeHolding(holding.id);
  }

  // ─── Empty State ──────────────────────────────────────────────────────────

  if (holdings.length === 0) {
    return (
      <div className="space-y-4">
        <div>
          <div className="text-2xl font-semibold">My Portfolio</div>
          <div className="text-muted-foreground text-sm">
            Track your holdings, sector allocation, and unrealized performance.
          </div>
        </div>

        {/* Compact empty state card */}
        <div className="bt-panel p-6 flex flex-col items-center text-center">
          <div className="h-12 w-12 rounded-2xl bg-muted/40 flex items-center justify-center mb-3">
            <Briefcase size={22} className="text-muted-foreground" />
          </div>
          <h3 className="text-base font-semibold mb-1">No holdings yet</h3>
          <p className="text-sm text-muted-foreground mb-4 max-w-xs">
            Add a position to see analytics, allocation, and AI insights.
          </p>
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="bt-button-primary w-full max-w-xs gap-2"
          >
            <Plus size={16} />
            Add Holding
          </button>
          <button
            type="button"
            className="flex items-center gap-1.5 mt-3 text-sm text-muted-foreground hover:text-foreground transition-colors"
            title="CSV import coming soon"
            disabled
          >
            <Upload size={14} />
            Import CSV
          </button>
        </div>

        {showForm && (
          <AddHoldingForm
            onAdd={handleAddHolding}
            onCancel={() => setShowForm(false)}
          />
        )}

        {/* Preview modules */}
        <PerformancePreview />

        <div className="flex gap-2">
          {[
            { label: "P&L", icon: BarChart3 },
            { label: "Allocation", icon: PieChart },
            { label: "Risk", icon: ShieldAlert },
          ].map(({ label, icon: Icon }) => (
            <div
              key={label}
              className="flex-1 bt-panel p-3 flex items-center gap-2 opacity-40"
            >
              <Icon size={14} className="text-muted-foreground" />
              <span className="text-xs text-muted-foreground">{label}</span>
            </div>
          ))}
        </div>

        <div className="text-xs text-muted-foreground">
          {COMPLIANCE.PORTFOLIO_DISCLAIMER}
        </div>
      </div>
    );
  }

  // ─── Populated State ──────────────────────────────────────────────────────

  const contributors = summary?.contributors;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-2xl font-semibold">My Portfolio</div>
          <div className="text-muted-foreground text-sm">
            Track your holdings, sector allocation, and unrealized performance.
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowForm(!showForm)}
          className="bt-button gap-2"
        >
          <Plus size={14} />
          Add Holding
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <AddHoldingForm
          onAdd={handleAddHolding}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* KPI Cards */}
      {summary && <PortfolioKpiCards totals={summary.totals} />}

      {/* Loading skeleton for KPIs */}
      {summaryLoading && !summary && (
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bt-panel p-4">
              <div className="h-3 w-16 bg-muted/40 rounded animate-pulse mb-2" />
              <div className="h-5 w-24 bg-muted/40 rounded animate-pulse" />
            </div>
          ))}
        </div>
      )}

      {/* Main Grid: Left column + Right column */}
      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Left column */}
        <div className="space-y-6">
          {/* AI Brief */}
          <PortfolioAIBrief
            brief={brief}
            isLoading={briefLoading}
            error={briefError}
          />

          {/* Top Contributors / Detractors */}
          {contributors &&
            (contributors.topGainers.length > 0 ||
              contributors.topLosers.length > 0) && (
              <div className="grid gap-3 sm:grid-cols-2">
                {contributors.topGainers.length > 0 && (
                  <div className="bt-panel p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingUp size={14} className="text-risk-on" />
                      <span className="bt-panel-title">Top Contributors</span>
                    </div>
                    <div className="space-y-1.5">
                      {contributors.topGainers.map((g) => (
                        <div
                          key={g.ticker}
                          className="flex items-center justify-between text-xs"
                        >
                          <span className="font-mono font-semibold">
                            {g.ticker}
                          </span>
                          <span className="font-mono text-risk-on">
                            {formatCurrency(g.pl)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {contributors.topLosers.length > 0 && (
                  <div className="bt-panel p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <TrendingDown size={14} className="text-risk-off" />
                      <span className="bt-panel-title">Top Detractors</span>
                    </div>
                    <div className="space-y-1.5">
                      {contributors.topLosers.map((l) => (
                        <div
                          key={l.ticker}
                          className="flex items-center justify-between text-xs"
                        >
                          <span className="font-mono font-semibold">
                            {l.ticker}
                          </span>
                          <span className="font-mono text-risk-off">
                            {formatCurrency(l.pl)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

          {/* Concentration Flags */}
          {summary && summary.concentration.flags.length > 0 && (
            <div className="bt-panel p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle size={14} className="text-risk-neutral" />
                <span className="bt-panel-title">Concentration Notes</span>
              </div>
              <div className="space-y-1">
                {summary.concentration.flags.map((flag) => (
                  <div key={flag} className="text-xs text-muted-foreground">
                    {flag === "TOP_HOLDING_OVER_25" &&
                      `Your top holding represents ${summary.concentration.topHoldingWeightPct.toFixed(1)}% of portfolio value.`}
                    {flag === "TOP_3_OVER_65" &&
                      `Your top 3 holdings represent ${summary.concentration.top3WeightPct.toFixed(1)}% of portfolio value.`}
                    {flag === "SECTOR_OVER_40" &&
                      `Your largest sector represents ${summary.concentration.maxSectorWeightPct.toFixed(1)}% of portfolio value.`}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sector Drilldown */}
          {selectedSector && summary && (
            <SectorDrilldown
              sector={selectedSector}
              holdings={summary.holdings}
              onClose={() => setSelectedSector(null)}
            />
          )}

          {/* Holdings Table */}
          {summary && (
            <HoldingsTable
              holdings={summary.holdings}
              onRemoveHolding={handleRemoveHolding}
            />
          )}
        </div>

        {/* Right column: Pie chart */}
        <div className="space-y-6">
          {summary && (
            <SectorAllocationPie
              allocations={summary.sectorAllocations}
              selectedSector={selectedSector}
              onSelectSector={setSelectedSector}
            />
          )}
        </div>
      </div>

      <div className="text-xs text-muted-foreground">
        {COMPLIANCE.PORTFOLIO_DISCLAIMER}
      </div>
    </div>
  );
}

// ─── Page Export ──────────────────────────────────────────────────────────────

export default function PortfolioPage() {
  return (
    <PortfolioProvider>
      <PortfolioContent />
    </PortfolioProvider>
  );
}
