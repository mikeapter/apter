import {
  Activity,
  Gauge,
  Eye,
  Newspaper,
  ShieldCheck,
  FileText,
} from "lucide-react";

const FEATURES = [
  {
    Icon: Activity,
    title: "Regime detection",
    description:
      "Automated classification of market environments into risk-on, neutral, and risk-off states.",
  },
  {
    Icon: Gauge,
    title: "Signal confidence scoring",
    description:
      "Every signal includes a confidence metric so you can weigh conviction before acting.",
  },
  {
    Icon: Eye,
    title: "Watchlist monitoring",
    description:
      "Track your preferred tickers and receive signals scoped to your focus universe.",
  },
  {
    Icon: Newspaper,
    title: "News & event context",
    description:
      "Macro events and news catalysts are surfaced alongside signals for situational awareness.",
  },
  {
    Icon: ShieldCheck,
    title: "Risk controls checklist",
    description:
      "Pre-trade risk checks including position limits, volatility thresholds, and correlation filters.",
  },
  {
    Icon: FileText,
    title: "Explainable rationale",
    description:
      "No black box. Every signal comes with a plain-language explanation of why it was generated.",
  },
] as const;

export default function FeatureGrid() {
  return (
    <section id="features" className="py-20 border-t border-border">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <div className="max-w-lg mb-12">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-2">
            Product
          </p>
          <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
            Everything you need, nothing you don&apos;t
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((feat) => (
            <div
              key={feat.title}
              className="rounded-lg border border-border bg-card p-5 flex flex-col gap-3 transition-colors duration-150 hover:border-ring/40"
            >
              <div className="h-10 w-10 rounded-md bg-panel border border-border flex items-center justify-center">
                <feat.Icon className="h-5 w-5 text-muted-foreground" />
              </div>
              <h3 className="text-sm font-semibold text-foreground">
                {feat.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {feat.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
