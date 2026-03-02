"use client";

import { Sparkles, AlertTriangle } from "lucide-react";
import type { AIBriefResponse } from "../../lib/api/portfolio";

type Props = {
  brief: AIBriefResponse | null;
  isLoading: boolean;
  error: string | null;
};

export function PortfolioAIBrief({ brief, isLoading, error }: Props) {
  return (
    <div className="bt-panel p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={14} className="text-muted-foreground" />
        <span className="bt-panel-title">Portfolio Brief</span>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-4 rounded bg-muted/40 animate-pulse"
              style={{ width: `${90 - i * 10}%` }}
            />
          ))}
        </div>
      )}

      {error && (
        <div className="flex items-start gap-2 text-xs text-muted-foreground">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span>Unable to generate portfolio brief. Please try again.</span>
        </div>
      )}

      {brief && !isLoading && (
        <>
          <ul className="space-y-2">
            {brief.bullets.map((bullet, i) => (
              <li key={i} className="flex gap-2 text-sm leading-relaxed">
                <span className="text-muted-foreground mt-0.5 shrink-0">
                  &bull;
                </span>
                <span>{bullet}</span>
              </li>
            ))}
          </ul>
          <div className="mt-3 text-[10px] text-muted-foreground">
            {brief.disclaimer}
          </div>
        </>
      )}
    </div>
  );
}
