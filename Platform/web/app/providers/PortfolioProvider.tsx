"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { PortfolioHolding } from "../lib/dashboard";
import { getMockPrice, getMockGrade } from "../lib/stockData";

const LS_KEY = "apter_portfolio";

export type EnrichedHolding = PortfolioHolding & {
  currentPrice: number;
  positionValue: number;
  costBasis: number;
  unrealizedPL: number;
  unrealizedPLPct: number;
  grade: number;
};

type PortfolioContextValue = {
  holdings: EnrichedHolding[];
  totalValue: number;
  totalCost: number;
  totalPL: number;
  totalPLPct: number;
  addHolding: (ticker: string, shares: number, purchasePrice: number) => void;
  removeHolding: (id: string) => void;
  updateHolding: (id: string, updates: Partial<Pick<PortfolioHolding, "shares" | "purchasePrice">>) => void;
};

const PortfolioContext = createContext<PortfolioContextValue | null>(null);

function generateId(): string {
  return `h_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function loadHoldings(): PortfolioHolding[] {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (h: any) => h && typeof h.ticker === "string" && typeof h.shares === "number" && typeof h.purchasePrice === "number"
    );
  } catch {
    return [];
  }
}

function saveHoldings(holdings: PortfolioHolding[]) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(holdings));
  } catch {}
}

function enrichHolding(h: PortfolioHolding): EnrichedHolding {
  const currentPrice = getMockPrice(h.ticker);
  const costBasis = h.shares * h.purchasePrice;
  const positionValue = h.shares * currentPrice;
  const unrealizedPL = positionValue - costBasis;
  const unrealizedPLPct = costBasis > 0 ? (unrealizedPL / costBasis) * 100 : 0;
  const grade = getMockGrade(h.ticker);

  return {
    ...h,
    currentPrice,
    positionValue,
    costBasis,
    unrealizedPL,
    unrealizedPLPct,
    grade,
  };
}

export function PortfolioProvider({ children }: { children: React.ReactNode }) {
  const [raw, setRaw] = useState<PortfolioHolding[]>([]);

  useEffect(() => {
    setRaw(loadHoldings());
  }, []);

  const persist = useCallback((next: PortfolioHolding[]) => {
    setRaw(next);
    saveHoldings(next);
  }, []);

  const addHolding = useCallback(
    (ticker: string, shares: number, purchasePrice: number) => {
      const h: PortfolioHolding = {
        id: generateId(),
        ticker: ticker.toUpperCase().trim(),
        shares,
        purchasePrice,
        addedAt: new Date().toISOString(),
      };
      persist([...raw, h]);
    },
    [raw, persist]
  );

  const removeHolding = useCallback(
    (id: string) => {
      persist(raw.filter((h) => h.id !== id));
    },
    [raw, persist]
  );

  const updateHolding = useCallback(
    (id: string, updates: Partial<Pick<PortfolioHolding, "shares" | "purchasePrice">>) => {
      persist(
        raw.map((h) => (h.id === id ? { ...h, ...updates } : h))
      );
    },
    [raw, persist]
  );

  const holdings = useMemo(() => raw.map(enrichHolding), [raw]);

  const totalValue = useMemo(() => holdings.reduce((sum, h) => sum + h.positionValue, 0), [holdings]);
  const totalCost = useMemo(() => holdings.reduce((sum, h) => sum + h.costBasis, 0), [holdings]);
  const totalPL = totalValue - totalCost;
  const totalPLPct = totalCost > 0 ? (totalPL / totalCost) * 100 : 0;

  const value = useMemo(
    () => ({ holdings, totalValue, totalCost, totalPL, totalPLPct, addHolding, removeHolding, updateHolding }),
    [holdings, totalValue, totalCost, totalPL, totalPLPct, addHolding, removeHolding, updateHolding]
  );

  return <PortfolioContext.Provider value={value}>{children}</PortfolioContext.Provider>;
}

export function usePortfolio() {
  const ctx = useContext(PortfolioContext);
  if (!ctx) throw new Error("usePortfolio must be used inside <PortfolioProvider>");
  return ctx;
}
