import { COMPLIANCE } from "../../lib/compliance";

export function FooterGuidance() {
  return (
    <footer className="h-10 border-t border-border bg-panel px-4 flex items-center">
      <div className="text-xs text-muted-foreground">{COMPLIANCE.GLOBAL_FOOTER}</div>
    </footer>
  );
}
