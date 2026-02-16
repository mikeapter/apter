import Link from "next/link";

export default function Hero() {
  return (
    <section className="relative pt-32 pb-20 sm:pt-40 sm:pb-28">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-foreground leading-[1.15]">
            Disciplined Trading Intelligence, Built for Control
          </h1>
          <p className="mt-5 text-base sm:text-lg text-muted-foreground leading-relaxed max-w-xl">
            Rules-based signals with regime context and transparent
            rationale&mdash;so you decide when to execute.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-start gap-3">
            <Link
              href="/signup"
              className="inline-flex h-12 items-center justify-center rounded-md bg-foreground text-background px-6 text-sm font-medium transition-opacity duration-150 hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              data-track="cta_get_started_click"
            >
              Get Started For Free
            </Link>
            <Link
              href="#pricing"
              className="inline-flex h-12 items-center justify-center rounded-md border border-border bg-transparent px-6 text-sm font-medium text-foreground transition-colors duration-150 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              View Plans
            </Link>
          </div>

          {/* Trust strip */}
          <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-risk-on" aria-hidden="true" />
              No brokerage required
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-risk-on" aria-hidden="true" />
              Cancel anytime
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-risk-neutral" aria-hidden="true" />
              Not investment advice
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
