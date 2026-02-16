import Link from "next/link";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

type Tier = {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  cta: string;
  highlighted?: boolean;
};

const TIERS: Tier[] = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Evaluate methodology and build trust before commitment.",
    features: [
      "Daily market regime overview",
      "Delayed signal samples (24h lag)",
      "Plain-language model explanations",
      "Educational risk content",
    ],
    cta: "Get Started",
  },
  {
    name: "Analyst",
    price: "$25",
    period: "/month",
    description: "Real-time signals with full coverage and alert notifications.",
    features: [
      "Everything in Free",
      "Real-time signal feed",
      "Comprehensive daily coverage",
      "Regime confidence context",
      "Signal change alerts",
      "7-day signal history",
    ],
    cta: "Get Started",
    highlighted: true,
  },
  {
    name: "Pro",
    price: "$49",
    period: "/month",
    description: "Deep analytics, extended history, and priority access.",
    features: [
      "Everything in Analyst",
      "Extended historical archive",
      "Confidence bands & analytics",
      "Strategic drawdown commentary",
      "Priority feature access",
      "Priority support",
    ],
    cta: "Get Started",
  },
];

export default function PricingTeaser() {
  return (
    <section id="pricing" className="py-20 border-t border-border">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <div className="max-w-lg mb-12">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground mb-2">
            Pricing
          </p>
          <h2 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
            Transparent, simple pricing
          </h2>
          <p className="mt-3 text-sm text-muted-foreground">
            Start free. Upgrade when ready. Cancel anytime.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className={cn(
                "rounded-lg border p-6 flex flex-col",
                tier.highlighted
                  ? "border-ring bg-panel"
                  : "border-border bg-card"
              )}
            >
              <div className="mb-4">
                <h3 className="text-base font-semibold text-foreground">
                  {tier.name}
                </h3>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-foreground">
                    {tier.price}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {tier.period}
                  </span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                  {tier.description}
                </p>
              </div>

              <ul className="flex-1 space-y-2.5 mb-6">
                {tier.features.map((feat) => (
                  <li
                    key={feat}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    <Check
                      className="h-4 w-4 mt-0.5 shrink-0 text-risk-on"
                      aria-hidden="true"
                    />
                    {feat}
                  </li>
                ))}
              </ul>

              <Link
                href="/signup"
                className={cn(
                  "inline-flex h-11 items-center justify-center rounded-md px-4 text-sm font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  tier.highlighted
                    ? "bg-foreground text-background hover:opacity-90"
                    : "border border-border bg-transparent text-foreground hover:bg-muted"
                )}
              >
                {tier.cta}
              </Link>
            </div>
          ))}
        </div>

        <div className="mt-8 text-center">
          <Link
            href="/plans"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors duration-150 underline underline-offset-4"
          >
            Compare plans in detail
          </Link>
        </div>
      </div>
    </section>
  );
}
