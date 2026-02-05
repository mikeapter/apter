import type { SystemHistory } from "../../lib/dashboard";

export function SystemHistoryPanel({ history }: { history: SystemHistory }) {
  return (
    <section className="bt-panel p-4">
      <div className="bt-panel-title">SYSTEM HISTORY</div>

      <div className="mt-4 space-y-4">
        {/* Regime transitions */}
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Previous market regime transitions
          </div>

          <div className="mt-2 overflow-auto border border-border rounded-md">
            <table className="w-full text-sm">
              <thead className="bg-panel-2">
                <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  <th className="text-left px-3 py-2 font-medium">Timestamp</th>
                  <th className="text-left px-3 py-2 font-medium">From</th>
                  <th className="text-left px-3 py-2 font-medium">To</th>
                  <th className="text-left px-3 py-2 font-medium">Note</th>
                </tr>
              </thead>
              <tbody>
                {history.transitions.map((t, i) => (
                  <tr key={`${t.timestamp}-${i}`} className="border-t border-border">
                    <td className="px-3 py-2 font-mono text-[12px] text-muted-foreground">{t.timestamp}</td>
                    <td className="px-3 py-2 font-semibold">{t.from}</td>
                    <td className="px-3 py-2 font-semibold">{t.to}</td>
                    <td className="px-3 py-2 text-muted-foreground">{t.note}</td>
                  </tr>
                ))}
                {history.transitions.length === 0 && (
                  <tr className="border-t border-border">
                    <td colSpan={4} className="px-3 py-4 text-sm text-muted-foreground">
                      No transitions recorded.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* No-trade periods */}
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Historical “No Trade” periods
          </div>

          <div className="mt-2 overflow-auto border border-border rounded-md">
            <table className="w-full text-sm">
              <thead className="bg-panel-2">
                <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  <th className="text-left px-3 py-2 font-medium">Start</th>
                  <th className="text-left px-3 py-2 font-medium">End</th>
                  <th className="text-left px-3 py-2 font-medium">Reason</th>
                </tr>
              </thead>
              <tbody>
                {history.noTradePeriods.map((p, i) => (
                  <tr key={`${p.start}-${i}`} className="border-t border-border">
                    <td className="px-3 py-2 font-mono text-[12px] text-muted-foreground">{p.start}</td>
                    <td className="px-3 py-2 font-mono text-[12px] text-muted-foreground">{p.end}</td>
                    <td className="px-3 py-2 text-muted-foreground">{p.reason}</td>
                  </tr>
                ))}
                {history.noTradePeriods.length === 0 && (
                  <tr className="border-t border-border">
                    <td colSpan={3} className="px-3 py-4 text-sm text-muted-foreground">
                      No no-trade periods recorded.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Signal frequency analysis */}
        <div>
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Signal frequency analysis over time
          </div>

          <div className="mt-2 overflow-auto border border-border rounded-md">
            <table className="w-full text-sm">
              <thead className="bg-panel-2">
                <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                  <th className="text-left px-3 py-2 font-medium">Window</th>
                  <th className="text-left px-3 py-2 font-medium">Count</th>
                  <th className="text-left px-3 py-2 font-medium">Comment</th>
                </tr>
              </thead>
              <tbody>
                {history.signalFrequency.map((f, i) => (
                  <tr key={`${f.window}-${i}`} className="border-t border-border">
                    <td className="px-3 py-2 font-semibold">{f.window}</td>
                    <td className="px-3 py-2 font-mono text-[12px] text-muted-foreground">{f.count}</td>
                    <td className="px-3 py-2 text-muted-foreground">{f.comment}</td>
                  </tr>
                ))}
                {history.signalFrequency.length === 0 && (
                  <tr className="border-t border-border">
                    <td colSpan={3} className="px-3 py-4 text-sm text-muted-foreground">
                      No frequency data available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* No performance charts / equity curves by design */}
        <div className="text-xs text-muted-foreground">
          Process integrity is prioritized over promotional performance presentation.
        </div>
      </div>
    </section>
  );
}
