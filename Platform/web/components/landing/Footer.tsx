import Link from "next/link";
import Image from "next/image";

export default function Footer() {
  return (
    <footer className="border-t border-border py-12">
      <div className="mx-auto max-w-[1200px] px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="sm:col-span-2 lg:col-span-1">
            <div className="flex items-center gap-2.5 mb-3">
              <Image
                src="/logo.png"
                alt="Apter Financial"
                width={32}
                height={32}
                className="h-8 w-8 rounded-full"
              />
              <span className="text-sm font-semibold text-foreground">
                Apter Financial
              </span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed max-w-xs">
              Signals-only trading intelligence. We provide analytical tools and
              informational signals. We do not execute trades on your behalf.
            </p>
          </div>

          {/* Product */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground mb-3">
              Product
            </h4>
            <ul className="space-y-2">
              <li>
                <Link
                  href="#features"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors duration-150"
                >
                  Features
                </Link>
              </li>
              <li>
                <Link
                  href="#pricing"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors duration-150"
                >
                  Pricing
                </Link>
              </li>
              <li>
                <Link
                  href="#how-it-works"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors duration-150"
                >
                  How It Works
                </Link>
              </li>
            </ul>
          </div>

          {/* Legal */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground mb-3">
              Legal
            </h4>
            <ul className="space-y-2">
              <li>
                <Link
                  href="/terms"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors duration-150"
                >
                  Terms of Service
                </Link>
              </li>
              <li>
                <Link
                  href="/privacy"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors duration-150"
                >
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link
                  href="/disclaimer"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors duration-150"
                >
                  Disclaimer
                </Link>
              </li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground mb-3">
              Support
            </h4>
            <ul className="space-y-2">
              <li>
                <Link
                  href="mailto:support@apterfinancial.com"
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors duration-150"
                >
                  Contact Us
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Compliance banner */}
        <div className="mt-10 pt-6 border-t border-border">
          <p className="text-[11px] text-muted-foreground leading-relaxed max-w-3xl">
            Apter Financial provides analytical tools and informational signals
            only. Nothing on this platform constitutes investment advice,
            solicitation, or recommendation to buy or sell any security. All
            trading decisions are made independently by the user. Past signal
            performance does not guarantee future results. Trading involves
            significant risk of loss.
          </p>
          <p className="mt-3 text-[11px] text-muted-foreground">
            &copy; {new Date().getFullYear()} Apter Financial. All rights
            reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
