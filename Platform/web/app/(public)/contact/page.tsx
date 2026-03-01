import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Contact — Apter Financial",
};

export default function ContactPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      <header className="mb-10">
        <h1 className="text-2xl sm:text-3xl font-bold text-foreground">
          Contact Us
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          We&apos;re here to help. Reach out through any of the channels below.
        </p>
      </header>

      <div className="space-y-8">
        {/* Email support */}
        <div className="rounded-lg border border-border bg-card p-6">
          <h2 className="text-base font-semibold text-foreground mb-2">
            Email Support
          </h2>
          <p className="text-sm text-muted-foreground mb-4">
            For account questions, technical issues, or general inquiries.
          </p>
          <a
            href="mailto:support@apterfinancial.com"
            className="inline-flex items-center gap-2 text-sm font-medium text-foreground underline underline-offset-2 hover:opacity-80"
          >
            support@apterfinancial.com
          </a>
          <p className="mt-3 text-xs text-muted-foreground">
            We aim to respond within 1&ndash;2 business days.
          </p>
        </div>

        {/* Bug reports / feedback */}
        <div className="rounded-lg border border-border bg-card p-6">
          <h2 className="text-base font-semibold text-foreground mb-2">
            Bug Reports &amp; Feedback
          </h2>
          <p className="text-sm text-muted-foreground">
            Found a bug or have a feature suggestion? Email us at{" "}
            <a
              href="mailto:support@apterfinancial.com"
              className="text-foreground underline underline-offset-2 hover:opacity-80"
            >
              support@apterfinancial.com
            </a>{" "}
            with the subject line &quot;Bug Report&quot; or &quot;Feature
            Request&quot; and include as much detail as possible.
          </p>
        </div>

        {/* Business inquiries */}
        <div className="rounded-lg border border-border bg-card p-6">
          <h2 className="text-base font-semibold text-foreground mb-2">
            Business Inquiries
          </h2>
          <p className="text-sm text-muted-foreground">
            For partnership, media, or other business-related inquiries, reach out
            to{" "}
            <a
              href="mailto:support@apterfinancial.com"
              className="text-foreground underline underline-offset-2 hover:opacity-80"
            >
              support@apterfinancial.com
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
