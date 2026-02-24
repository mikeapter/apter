import Link from "next/link";

export function PublicFooter() {
  return (
    <footer className="border-t border-border bg-panel px-4 py-6">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} Apter Financial. All rights reserved.
        </div>
        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <Link href="/terms" className="hover:text-foreground">Terms</Link>
          <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
          <Link href="/risk-disclosure" className="hover:text-foreground">Risk Disclosure</Link>
          <Link href="/about" className="hover:text-foreground">About</Link>
          <Link href="/contact" className="hover:text-foreground">Contact</Link>
        </div>
      </div>
      <div className="max-w-5xl mx-auto mt-4">
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Apter Financial provides analytical tools and informational signals
          only. Not investment advice. Past performance does not guarantee future
          results. Trading involves significant risk of loss.
        </p>
      </div>
    </footer>
  );
}
