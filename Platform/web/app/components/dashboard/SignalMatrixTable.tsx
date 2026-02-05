import type { SignalRow } from "../../lib/dashboard";

function signalTone(signal: SignalRow["signal"]) {
  // Keep monotone. Only muted semantic color if desired.
  // BUY/SELL remain text (no charts, no motion).
  if (signal === "BUY") return "text-risk-on";
  if (signal === "SELL") return "text-risk-off";
  return "text-foreground";
}

export function SignalMatrixTable({ rows }: { rows: SignalRow[] }) {
  return (
    <section className="bt-panel p-4">
      <div className="bt-panel-title">SIGNAL MATRIX</div>

      <div className="mt-3 overflow-auto border border-border rounded-md">
        <table className="w-full text-sm">
          <thead className="bg-panel-2">
            <tr className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
              <th className="text-left px-3 py-2 font-medium">Ticker</th>
              <th className="text-left px-3 py-2 font-medium">Signal</th>
              <th className="text-left px-3 py-2 font-medium">Timestamp</th>
              <th className="text-left px-3 py-2 font-medium">Confidence</th>
            </tr>
          </thead>

          <tbody>
            {rows.slice(0, 50).map((r, idx) => (
              <tr key={`${r.ticker}-${idx}`} className="border-t border-border">
                <td className="px-3 py-2 font-mono text-[12px] font-semibold">
                  {r.ticker}
                </td>
                <td className={`px-3 py-2 font-semibold ${signalTone(r.signal)}`}>
                  {r.signal}
                </td>
                <td className="px-3 py-2 font-mono text-[12px] text-muted-foreground">
                  {r.timestamp}
                </td>
                <td className="px-3 py-2">
                  <span className="bt-chip border-border text-foreground">
                    <span className="font-semibold">{r.confidence}</span>
                  </span>
                </td>
              </tr>
            ))}

            {rows.length === 0 && (
              <tr className="border-t border-border">
                <td colSpan={4} className="px-3 py-6 text-sm text-muted-foreground">
                  No signals available under current conditions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
