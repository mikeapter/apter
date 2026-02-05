"use client";

import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { DashboardData, normalizeDashboardData, sampleDashboardData } from "../lib/dashboard";

type DashboardContextValue = {
  data: DashboardData;
  lastUpdatedAt: number; // ms epoch
  source: "api" | "sample";
  error?: string;
  refresh: () => Promise<void>;
};

const DashboardContext = createContext<DashboardContextValue | null>(null);

export function DashboardDataProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<DashboardData>(sampleDashboardData);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<number>(() => Date.now() - 45_000);
  const [source, setSource] = useState<"api" | "sample">("sample");
  const [error, setError] = useState<string | undefined>(undefined);

  const inFlight = useRef(false);

  async function refresh() {
    if (inFlight.current) return;
    inFlight.current = true;

    try {
      setError(undefined);

      // NOTE: If your Next rewrites proxy /api/* to FastAPI, this will hit FastAPI directly.
      // If you keep a Next route handler for /api/dashboard, it can also work.
      const r = await fetch("/api/dashboard", { cache: "no-store" });

      if (!r.ok) throw new Error(`Dashboard fetch failed (HTTP ${r.status})`);

      const payload = await r.json();
      const normalized = normalizeDashboardData(payload);

      if (normalized) {
        setData(normalized);
        setSource("api");
        setLastUpdatedAt(Date.now());
      } else {
        // Unknown shape; keep current data but mark sample to remain conservative.
        setSource("sample");
        setLastUpdatedAt(Date.now());
      }
    } catch (e: any) {
      setError(String(e?.message ?? e));
      setSource("sample");
      // Keep existing data (sample) so UI remains stable.
    } finally {
      inFlight.current = false;
    }
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 30_000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = useMemo(
    () => ({ data, lastUpdatedAt, source, error, refresh }),
    [data, lastUpdatedAt, source, error]
  );

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboardData() {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboardData must be used inside <DashboardDataProvider>");
  return ctx;
}
