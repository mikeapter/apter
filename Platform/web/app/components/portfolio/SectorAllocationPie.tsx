"use client";

import { useCallback } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import type { SectorAllocation } from "../../lib/api/portfolio";

const SECTOR_COLORS: Record<string, string> = {
  Technology: "#6366f1",
  "Consumer Discretionary": "#f59e0b",
  Financials: "#10b981",
  Healthcare: "#ef4444",
  "Consumer Staples": "#8b5cf6",
  Energy: "#f97316",
  "Communication Services": "#06b6d4",
  Industrials: "#64748b",
  Materials: "#a3e635",
  "Real Estate": "#e879f9",
  Utilities: "#2dd4bf",
  "Broad Market ETF": "#94a3b8",
  "Technology ETF": "#818cf8",
  Other: "#475569",
};

function getColor(sector: string): string {
  return SECTOR_COLORS[sector] ?? SECTOR_COLORS["Other"];
}

type Props = {
  allocations: SectorAllocation[];
  selectedSector: string | null;
  onSelectSector: (sector: string | null) => void;
};

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: SectorAllocation }>;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bt-panel p-2 text-xs shadow-lg">
      <div className="font-semibold">{d.sector}</div>
      <div className="text-muted-foreground">
        {d.weightPct.toFixed(1)}% &middot; $
        {d.marketValue.toLocaleString("en-US", { minimumFractionDigits: 0 })}
      </div>
    </div>
  );
}

export function SectorAllocationPie({
  allocations,
  selectedSector,
  onSelectSector,
}: Props) {
  const handleClick = useCallback(
    (entry: SectorAllocation) => {
      onSelectSector(
        selectedSector === entry.sector ? null : entry.sector,
      );
    },
    [selectedSector, onSelectSector],
  );

  if (allocations.length === 0) return null;

  return (
    <div className="bt-panel p-4">
      <div className="bt-panel-title mb-3">Sector Allocation</div>

      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={allocations}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={85}
            paddingAngle={2}
            dataKey="weightPct"
            nameKey="sector"
            onClick={(_data: unknown, index: number) =>
              handleClick(allocations[index])
            }
            style={{ cursor: "pointer", outline: "none" }}
          >
            {allocations.map((entry) => (
              <Cell
                key={entry.sector}
                fill={getColor(entry.sector)}
                stroke={
                  selectedSector === entry.sector
                    ? "hsl(var(--foreground))"
                    : "transparent"
                }
                strokeWidth={selectedSector === entry.sector ? 2 : 0}
                opacity={
                  selectedSector && selectedSector !== entry.sector ? 0.4 : 1
                }
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="mt-3 space-y-1.5">
        {allocations.map((a) => (
          <button
            key={a.sector}
            type="button"
            onClick={() => handleClick(a)}
            className={`flex w-full items-center justify-between rounded px-2 py-1 text-xs transition-colors hover:bg-muted/40 ${
              selectedSector === a.sector ? "bg-muted/40" : ""
            }`}
          >
            <span className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ backgroundColor: getColor(a.sector) }}
              />
              <span className="truncate">{a.sector}</span>
            </span>
            <span className="font-mono text-muted-foreground">
              {a.weightPct.toFixed(1)}%
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
