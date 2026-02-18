"use client";

import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, AlertTriangle, Shield } from "lucide-react";
import { authGet } from "@/lib/fetchWithAuth";

type BandInfo = { label: string; color: string };
type PillarScores = { quality: number; value: number; growth: number; momentum: number; risk: number };
type DriverItem = { name: string; impact: number; detail: string };
type PenaltyOrCap = { type: string; name: string; value: number; reason: string };

type ConvictionScore = {
  ticker: string;
  overall_score: number;
  band: BandInfo;
  pillars: PillarScores;
  drivers: { positive: DriverItem[]; negative: DriverItem[] };
  penalties_and_caps_applied: PenaltyOrCap[];
  confidence: number;
  model_version: string;
  computed_at: string;
};

function bandColorClass(color: string): string {
  if (color === "green") return "text-risk-on border-risk-on/40 bg-risk-on/10";
  if (color === "red") return "text-risk-off border-risk-off/40 bg-risk-off/10";
  return "text-risk-neutral border-risk-neutral/40 bg-risk-neutral/10";
}

function scoreBarColor(score: number): string {
  if (score <= 3.9) return "bg-risk-off";
  if (score <= 7.9) return "bg-risk-neutral";
  return "bg-risk-on";
}

function PillarBar({ name, score }: { name: string; score: number }) {
  const pct = Math.min(100, Math.max(0, (score / 10) * 100));
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 text-[10px] uppercase tracking-[0.14em] text-muted-foreground">{name}</div>
      <div className="flex-1 h-2 bg-panel-2 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${scoreBarColor(score)}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="w-8 text-right font-mono text-[11px]">{score.toFixed(1)}</div>
    </div>
  );
}

export function ConvictionScoreCard({ ticker }: { ticker: string }) {
  const [data, setData] = useState<ConvictionScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    setError(null);

    authGet<ConvictionScore>(`/api/score/${encodeURIComponent(ticker)}`).then((res) => {
      if (res.ok) {
        setData(res.data);
      } else {
        setError(res.error || "Failed to load score");
      }
      setLoading(false);
    });
  }, [ticker]);

  if (loading) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">CONVICTION SCORE</div>
        <div className="mt-4 flex items-center justify-center py-8 text-muted-foreground text-sm">
          Loading score...
        </div>
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className="bt-panel p-4">
        <div className="bt-panel-title">CONVICTION SCORE</div>
        <div className="mt-4 text-sm text-muted-foreground">{error || "Score unavailable"}</div>
      </section>
    );
  }

  return (
    <section className="bt-panel p-4 space-y-4">
      <div className="bt-panel-title">APTER CONVICTION SCORE</div>

      {/* Big score */}
      <div className="flex items-center gap-4">
        <div className="text-4xl font-bold font-mono">{data.overall_score.toFixed(1)}</div>
        <div className="text-lg text-muted-foreground font-mono">/ 10</div>
        <span className={`ml-auto px-3 py-1 rounded-sm border text-xs font-semibold ${bandColorClass(data.band.color)}`}>
          {data.band.label}
        </span>
      </div>

      {/* Confidence + model */}
      <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
        <div className="flex items-center gap-1">
          <Shield size={10} />
          <span>Confidence: {data.confidence}%</span>
        </div>
        <span>&middot;</span>
        <span>{data.model_version}</span>
      </div>

      {/* Pillar bars */}
      <div className="space-y-2">
        <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Pillar Scores</div>
        <PillarBar name="Quality" score={data.pillars.quality} />
        <PillarBar name="Value" score={data.pillars.value} />
        <PillarBar name="Growth" score={data.pillars.growth} />
        <PillarBar name="Momentum" score={data.pillars.momentum} />
        <PillarBar name="Risk" score={data.pillars.risk} />
      </div>

      {/* Drivers */}
      {(data.drivers.positive.length > 0 || data.drivers.negative.length > 0) && (
        <div className="space-y-2">
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Key Drivers</div>
          {data.drivers.positive.slice(0, 3).map((d, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <TrendingUp size={12} className="text-risk-on mt-0.5 shrink-0" />
              <div>
                <span className="font-medium">{d.name}</span>
                <span className="text-muted-foreground ml-1">({d.impact > 0 ? "+" : ""}{d.impact.toFixed(1)})</span>
              </div>
            </div>
          ))}
          {data.drivers.negative.slice(0, 3).map((d, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <TrendingDown size={12} className="text-risk-off mt-0.5 shrink-0" />
              <div>
                <span className="font-medium">{d.name}</span>
                <span className="text-muted-foreground ml-1">({d.impact.toFixed(1)})</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Penalties/Caps */}
      {data.penalties_and_caps_applied.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium">Risk Adjustments</div>
          {data.penalties_and_caps_applied.map((p, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-risk-off">
              <AlertTriangle size={12} className="mt-0.5 shrink-0" />
              <div>
                <span className="font-medium">{p.name}</span>
                <span className="text-muted-foreground ml-1">
                  ({p.type === "cap" ? `capped at ${p.value}` : `${p.value}`})
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
