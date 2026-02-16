import {
  ShieldCheck,
  FileText,
  Activity,
  ListChecks,
} from "lucide-react";

const TRUST_POINTS = [
  {
    Icon: ShieldCheck,
    title: "Built for disciplined traders",
    description:
      "Designed around process and routine, not hype or gamification.",
  },
  {
    Icon: FileText,
    title: "Transparent signal rationale",
    description:
      "Every signal includes plain-language reasoning you can evaluate.",
  },
  {
    Icon: Activity,
    title: "Regime-aware analysis",
    description:
      "Market context (risk-on, neutral, risk-off) frames every signal.",
  },
  {
    Icon: ListChecks,
    title: "Structured risk-first workflow",
    description:
      "Risk controls and checklists before execution, every time.",
  },
] as const;

export default function SocialProof() {
  return (
    <section className="py-16 border-t border-border">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {TRUST_POINTS.map((item) => (
            <div key={item.title} className="flex flex-col gap-3">
              <div className="h-10 w-10 rounded-md bg-panel border border-border flex items-center justify-center">
                <item.Icon className="h-5 w-5 text-muted-foreground" />
              </div>
              <h3 className="text-sm font-semibold text-foreground">
                {item.title}
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
