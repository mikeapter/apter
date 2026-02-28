import { Metadata } from "next";

export const metadata: Metadata = {
  title: "About — Apter Financial",
};

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <header className="mb-10">
        <h1 className="text-2xl sm:text-3xl font-bold text-foreground">
          About Apter Financial
        </h1>
      </header>

      <div className="space-y-8 text-sm text-muted-foreground leading-relaxed">
        {/* Mission */}
        <section>
          <h2 className="text-base font-semibold text-foreground mb-3">
            Our Mission
          </h2>
          <p>
            Apter Financial exists to bring structured decision support to
            self-directed traders. Markets are noisy. Information is fragmented.
            We build tools that cut through the noise and surface what matters so
            you can make more disciplined trading decisions.
          </p>
        </section>

        {/* Origin */}
        <section>
          <h2 className="text-base font-semibold text-foreground mb-3">
            How We Started
          </h2>
          <p>
            Apter Financial was founder-built out of a straightforward
            frustration: retail traders face the same markets as institutions but
            with a fraction of the analytical tooling. We set out to close that
            gap — not by promising returns or running automated strategies, but by
            giving everyday traders access to clear, actionable signals and
            analytics they can trust.
          </p>
        </section>

        {/* What we do */}
        <section>
          <h2 className="text-base font-semibold text-foreground mb-3">
            What We Do
          </h2>
          <p className="mb-3">
            We provide analytical tools and informational signals — not investment
            advice. Our platform helps you:
          </p>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>
              Monitor market conditions with structured, data-driven signals.
            </li>
            <li>
              Track portfolio exposure and risk across your positions.
            </li>
            <li>
              Analyze historical patterns to inform — not dictate — your next
              move.
            </li>
          </ul>
          <p className="mt-3">
            Every trading decision remains yours. We provide the framework; you
            make the call.
          </p>
        </section>

        {/* Principles */}
        <section>
          <h2 className="text-base font-semibold text-foreground mb-3">
            Our Principles
          </h2>
          <ul className="list-disc pl-5 space-y-1.5">
            <li>
              <strong className="text-foreground">Transparency:</strong> We tell
              you exactly what our tools do and where the data comes from. No
              black boxes.
            </li>
            <li>
              <strong className="text-foreground">Honesty:</strong> We do not
              overpromise. Markets are uncertain, and we will never pretend
              otherwise.
            </li>
            <li>
              <strong className="text-foreground">User autonomy:</strong> You
              are in control. We support your decisions — we do not make them for
              you.
            </li>
            <li>
              <strong className="text-foreground">Simplicity:</strong> Clean
              tools that do their job well, without unnecessary complexity.
            </li>
          </ul>
        </section>

        {/* Contact */}
        <section>
          <h2 className="text-base font-semibold text-foreground mb-3">
            Get in Touch
          </h2>
          <p>
            Have questions or want to learn more? Reach us at{" "}
            <a
              href="mailto:support@apterfinancial.com"
              className="text-foreground underline underline-offset-2 hover:opacity-80"
            >
              support@apterfinancial.com
            </a>
            .
          </p>
        </section>
      </div>
    </div>
  );
}
