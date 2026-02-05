"use client";

import * as React from "react";
import type { AlertItem, AlertCategory, AlertPrefs } from "@/lib/alerts";
import { defaultPrefs, loadPrefs, savePrefs, shouldShowAlert } from "@/lib/alerts";
import { Button } from "@/components/ui/button";

function cx(...parts: Array<string | undefined | false>) {
  return parts.filter(Boolean).join(" ");
}

type Props = {
  alerts: AlertItem[];
  title?: string; // optional label in header area
};

const CATEGORY_LABELS: Record<AlertCategory, string> = {
  system: "System",
  account: "Account",
  subscription: "Subscription",
  data: "Data",
  security: "Security",
};

export function AlertCenter({ alerts, title = "Notices" }: Props) {
  const [prefs, setPrefs] = React.useState<AlertPrefs>(defaultPrefs());

  React.useEffect(() => {
    setPrefs(loadPrefs());
  }, []);

  function update(next: AlertPrefs) {
    setPrefs(next);
    savePrefs(next);
  }

  const visible = React.useMemo(() => {
    return alerts.filter((a) => shouldShowAlert(a, prefs));
  }, [alerts, prefs]);

  return (
    <section className="w-full rounded-md border border-[rgba(255,255,255,0.10)] bg-[rgba(255,255,255,0.05)] p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-semibold text-white">{title}</div>

        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-xs text-[rgba(255,255,255,0.75)]">
            <input
              type="checkbox"
              checked={prefs.enabled}
              onChange={(e) => update({ ...prefs, enabled: e.target.checked })}
            />
            Alerts enabled
          </label>
        </div>
      </div>

      {/* Category mute controls (text-only) */}
      <div className="mt-3 flex flex-wrap gap-2">
        {(Object.keys(CATEGORY_LABELS) as AlertCategory[]).map((cat) => {
          const muted = prefs.mutedCategories[cat];
          return (
            <button
              key={cat}
              className={cx(
                "institutional-interactive rounded-md border px-2 py-1 text-xs",
                "border-[rgba(255,255,255,0.10)]",
                muted ? "opacity-50" : "opacity-90"
              )}
              onClick={() =>
                update({
                  ...prefs,
                  mutedCategories: { ...prefs.mutedCategories, [cat]: !muted },
                })
              }
              type="button"
            >
              {CATEGORY_LABELS[cat]}{muted ? " (muted)" : ""}
            </button>
          );
        })}
      </div>

      <div className="mt-3 space-y-2">
        {visible.length === 0 ? (
          <div className="text-xs text-[rgba(255,255,255,0.70)]">
            No notices to display.
          </div>
        ) : (
          visible.map((a) => (
            <div
              key={a.id}
              className="rounded-md border border-[rgba(255,255,255,0.10)] bg-transparent p-2"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm text-white">{a.title}</div>
                  {a.body ? (
                    <div className="mt-1 text-xs text-[rgba(255,255,255,0.75)]">
                      {a.body}
                    </div>
                  ) : null}
                  <div className="mt-1 text-[11px] text-[rgba(255,255,255,0.60)]">
                    {CATEGORY_LABELS[a.category]} • {a.severity} • {new Date(a.createdAtISO).toLocaleString()}
                  </div>
                </div>

                {/* Optional acknowledge button (neutral label) */}
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    // Intentionally no confetti / toast / celebratory effect.
                    // In a real app you could mark acknowledged in state or backend.
                    // For now: do nothing besides allow the click.
                  }}
                >
                  Acknowledge
                </Button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="mt-3 text-[11px] text-[rgba(255,255,255,0.60)]">
        Alerts are text-only and intentionally low-disruption. No urgency language is used.
      </div>
    </section>
  );
}
