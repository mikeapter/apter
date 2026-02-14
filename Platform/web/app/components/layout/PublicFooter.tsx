export function PublicFooter() {
  return (
    <footer className="border-t border-border bg-panel px-4 py-6">
      <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} Apter Financial. All rights reserved.
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <a href="/terms" className="hover:text-foreground">Terms of Service</a>
          <a href="/privacy" className="hover:text-foreground">Privacy Policy</a>
          <a href="/help-support" className="hover:text-foreground">Support</a>
        </div>
      </div>
      <div className="max-w-5xl mx-auto mt-4">
        <p className="text-[11px] text-muted-foreground leading-relaxed">
          Information is for educational and research purposes only. Not investment advice.
          Apter Financial is not acting as a registered investment adviser. Past performance
          does not guarantee future results.
        </p>
      </div>
    </footer>
  );
}
