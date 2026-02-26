"use client";

import { useState } from "react";
import Link from "next/link";
import { Info } from "lucide-react";
import { Modal } from "../ui/Modal";
import { COMPLIANCE } from "../../lib/compliance";

const QUICK_PILLARS = [
  { name: "Quality", desc: "Business durability and efficiency (ROE, margins, ROIC)" },
  { name: "Value", desc: "Price reasonableness (P/E, P/B, FCF yield)" },
  { name: "Growth", desc: "Revenue and earnings trajectory" },
  { name: "Momentum", desc: "Trend strength and moving average positioning" },
  { name: "Risk", desc: "Volatility, leverage, and drawdown exposure" },
] as const;

const QUICK_BANDS = [
  { range: "8\u201310", label: "Strong Setup", color: "text-risk-on" },
  { range: "6\u20137.9", label: "Constructive", color: "text-risk-neutral" },
  { range: "4\u20135.9", label: "Neutral", color: "text-muted-foreground" },
  { range: "0\u20133.9", label: "Weak Setup", color: "text-risk-off" },
] as const;

export function MethodologyLink() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring rounded-sm"
        aria-label="Score methodology"
      >
        <Info size={11} />
        <span>Methodology</span>
      </button>

      <Modal open={open} onClose={() => setOpen(false)} title="Conviction Score Methodology">
        <div className="space-y-4">
          {/* Pillars */}
          <div>
            <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
              Five Pillars
            </div>
            <div className="space-y-1.5">
              {QUICK_PILLARS.map((p) => (
                <div key={p.name} className="flex items-start gap-2 text-xs">
                  <span className="font-medium w-20 shrink-0">{p.name}</span>
                  <span className="text-muted-foreground">{p.desc}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Bands */}
          <div>
            <div className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground font-medium mb-2">
              Score Bands
            </div>
            <div className="space-y-1">
              {QUICK_BANDS.map((b) => (
                <div key={b.range} className="flex items-center gap-3 text-xs">
                  <span className="font-mono w-14 shrink-0">{b.range}</span>
                  <span className={b.color}>{b.label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Update / horizon */}
          <div className="text-xs text-muted-foreground space-y-1">
            <p>
              Scores are updated regularly; frequency varies by data
              availability.
            </p>
            <p>
              Designed for swing and position-level analysis, not intraday
              trading.
            </p>
          </div>

          {/* Disclaimer */}
          <p className="text-[10px] text-muted-foreground border-t border-border pt-3">
            {COMPLIANCE.NOT_INVESTMENT_ADVICE}
          </p>

          {/* Full methodology link */}
          <Link
            href="/methodology"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground underline underline-offset-4"
            onClick={() => setOpen(false)}
          >
            Read full methodology
          </Link>
        </div>
      </Modal>
    </>
  );
}
