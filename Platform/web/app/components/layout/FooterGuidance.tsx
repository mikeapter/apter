"use client";

import { useDashboardData } from "../../providers/DashboardDataProvider";

export function FooterGuidance() {
  const { data } = useDashboardData();

  return (
    <footer className="h-10 border-t border-border bg-panel px-4 flex items-center">
      <div className="text-xs text-muted-foreground">{data.guidance}</div>
    </footer>
  );
}
