import { BarChart3, Search, CheckCircle2 } from "lucide-react";

const STEPS = [
  {
    number: "01",
    Icon: BarChart3,
    title: "Analyze market regime and context",
    description:
      "The system evaluates broad market conditions, volatility regime, and sector context to establish whether the environment favors risk-on, neutral, or risk-off positioning.",
  },
  {
    number: "02",
    Icon: Search,
    title: "Review explainable signal + confidence",
    description:
      "Each signal is delivered with a plain-language rationale, confidence score, and the regime context that produced it. No black-box outputs.",
  },
  {
    number: "03",
    Icon: CheckCircle2,
    title: "Execute independently with discipline",
    description:
      "You decide whether and when to act. The platform provides structured risk controls and checklists to support disciplined, process-driven execution.",
  },
] as const;

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 border-t border-border">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <div className="max-w-lg mb-12">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-2">
            How It Works
          </p>
          <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
            Three steps to structured conviction
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12">
          {STEPS.map((step) => (
            <div key={step.number} className="flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold text-muted-foreground tracking-widest">
                  {step.number}
                </span>
                <div className="h-10 w-10 rounded-md bg-panel border border-border flex items-center justify-center">
                  <step.Icon className="h-5 w-5 text-muted-foreground" />
                </div>
              </div>
              <h3 className="text-sm font-semibold text-foreground">
                {step.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {step.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
