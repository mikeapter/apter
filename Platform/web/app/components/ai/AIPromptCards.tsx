"use client";

import { BarChart3, TrendingUp, GitCompareArrows, ShieldAlert } from "lucide-react";

type PromptCard = {
  label: string;
  prompt: string;
  icon: React.ReactNode;
};

const CARDS: PromptCard[] = [
  {
    label: "Earnings recap",
    prompt: "Summarize recent earnings results and what the data shows for major tech companies.",
    icon: <BarChart3 size={14} />,
  },
  {
    label: "Explain metric",
    prompt: "Explain the P/E ratio, what it measures, and how it is commonly used in fundamental analysis.",
    icon: <TrendingUp size={14} />,
  },
  {
    label: "Compare tickers",
    prompt: "Compare the key financial metrics and recent performance data for AAPL and MSFT.",
    icon: <GitCompareArrows size={14} />,
  },
  {
    label: "Risk snapshot",
    prompt: "What are the current market volatility conditions and key risk factors to be aware of?",
    icon: <ShieldAlert size={14} />,
  },
];

type Props = {
  onSelect: (prompt: string) => void;
};

export function AIPromptCards({ onSelect }: Props) {
  return (
    <div className="grid grid-cols-2 gap-1.5 px-1">
      {CARDS.map((card) => (
        <button
          key={card.label}
          type="button"
          onClick={() => onSelect(card.prompt)}
          className="flex items-center gap-2 rounded-md border border-border bg-panel-2 px-2.5 py-2 text-left text-xs hover:bg-muted transition-colors"
        >
          <span className="text-muted-foreground shrink-0">{card.icon}</span>
          <span>{card.label}</span>
        </button>
      ))}
    </div>
  );
}
