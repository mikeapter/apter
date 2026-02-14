"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PublicHeader } from "./components/layout/PublicHeader";
import { PublicFooter } from "./components/layout/PublicFooter";
import { apiGet } from "@/lib/api";

type Plan = {
  tier: string;
  name: string;
  price_usd_month: number;
  target_user: string;
  features: string[];
};

export default function HomePage() {
  const [plans, setPlans] = useState<Plan[]>([]);

  useEffect(() => {
    apiGet<{ plans: Plan[] }>("/api/plans").then((r) => {
      if (r.ok) setPlans(r.data.plans);
    });
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <PublicHeader />

      <main className="flex-1">
        {/* Hero */}
        <section className="px-4 py-20 text-center">
          <div className="max-w-3xl mx-auto">
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight leading-tight">
              Disciplined Trading Signals
            </h1>
            <p className="mt-4 text-lg text-muted-foreground max-w-xl mx-auto">
              Rules-based market analysis delivered in real time.
              Review signals, assess regime context, and execute on your terms.
            </p>
            <div className="mt-8 flex items-center justify-center gap-3">
              <Link
                href="/register"
                className="bt-button border-risk-on/40 text-risk-on hover:bg-risk-on/10 px-6 py-3 text-base"
              >
                Get Started Free
              </Link>
              <Link
                href="/plans"
                className="bt-button hover:bg-muted px-6 py-3 text-base"
              >
                View Plans
              </Link>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="px-4 py-16 border-t border-border">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-center text-sm font-semibold uppercase tracking-[0.22em] text-muted-foreground mb-10">
              How It Works
            </h2>
            <div className="grid gap-8 md:grid-cols-3">
              {[
                {
                  step: "01",
                  title: "Signals Generated",
                  desc: "Our rules-based engine analyzes market conditions and produces buy/sell/hold signals across covered instruments.",
                },
                {
                  step: "02",
                  title: "You Review",
                  desc: "Access regime context, confidence levels, and rationale. No black boxes \u2014 every signal comes with an explanation.",
                },
                {
                  step: "03",
                  title: "You Execute",
                  desc: "Decide what to act on, when, and how. We provide analysis. You maintain full control of your trading decisions.",
                },
              ].map((item) => (
                <div key={item.step} className="bt-panel p-5">
                  <div className="text-xs text-muted-foreground tracking-[0.12em] mb-2">
                    STEP {item.step}
                  </div>
                  <div className="font-semibold mb-2">{item.title}</div>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing preview */}
        {plans.length > 0 && (
          <section className="px-4 py-16 border-t border-border">
            <div className="max-w-4xl mx-auto">
              <h2 className="text-center text-sm font-semibold uppercase tracking-[0.22em] text-muted-foreground mb-10">
                Plans
              </h2>
              <div className="grid gap-4 md:grid-cols-3">
                {plans.map((p) => {
                  const price =
                    p.price_usd_month === 0
                      ? "Free"
                      : `$${p.price_usd_month}/mo`;
                  return (
                    <div key={p.tier} className="bt-panel p-5 flex flex-col">
                      <div className="flex items-start justify-between mb-3">
                        <div className="text-lg font-semibold">{p.name}</div>
                        <div className="font-bold">{price}</div>
                      </div>
                      <p className="text-sm text-muted-foreground mb-4">
                        {p.target_user}
                      </p>
                      <ul className="text-sm text-muted-foreground space-y-1 list-disc pl-5 flex-1">
                        {p.features.slice(0, 4).map((f, i) => (
                          <li key={i}>{f}</li>
                        ))}
                      </ul>
                      <Link
                        href={p.price_usd_month === 0 ? "/register" : "/plans"}
                        className="bt-button hover:bg-muted mt-4 w-full justify-center"
                      >
                        {p.price_usd_month === 0 ? "Start Free" : "Learn More"}
                      </Link>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        )}
      </main>

      <PublicFooter />
    </div>
  );
}
