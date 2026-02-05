import type { DiagnosticCard } from "../../lib/dashboard";

function toneChip(tone?: DiagnosticCard["tone"]) {
  if (tone === "on") return "bt-chip bt-chip-on";
  if (tone === "off") return "bt-chip bt-chip-off";
  return "bt-chip bt-chip-neutral";
}

export function RiskDiagnosticsPanel({ items }: { items: DiagnosticCard[] }) {
  return (
    <section className="bt-panel p-4">
      <div className="bt-panel-title">RISK & ENVIRONMENT DIAGNOSTICS</div>

      <div className="mt-3 space-y-3">
        {items.slice(0, 12).map((c, i) => (
          <div key={`${c.label}-${i}`} className="rounded-md border border-border bg-panel-2 p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="text-sm font-semibold">{c.label}</div>
              <span className={toneChip(c.tone)}>
                <span className="font-semibold">{c.state}</span>
              </span>
            </div>
            <div className="mt-2 text-sm text-muted-foreground leading-relaxed">
              {c.summary}
            </div>
          </div>
        ))}

        {items.length === 0 && (
          <div className="rounded-md border border-border bg-panel-2 p-3 text-sm text-muted-foreground">
            No diagnostics available.
          </div>
        )}
      </div>
    </section>
  );
}
