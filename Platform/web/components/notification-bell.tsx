"use client";

import * as React from "react";

type NotificationItem = {
  id: string;
  text: string;
  time?: string;
  unread?: boolean;
};

export function NotificationBell({
  items,
  onMarkAllRead,
}: {
  items: NotificationItem[];
  onMarkAllRead?: () => void;
}) {
  const [open, setOpen] = React.useState(false);

  const unreadCount = items.filter((x) => x.unread).length;

  // Close dropdown when clicking outside
  const ref = React.useRef<HTMLDivElement | null>(null);
  React.useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        className="relative inline-flex items-center justify-center rounded-xl border border-white/10 bg-white/5 px-3 py-2 hover:bg-white/10"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
      >
        <span className="text-sm">🔔</span>
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 rounded-full bg-red-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-[320px] rounded-2xl border border-white/10 bg-black/90 p-3 shadow-xl backdrop-blur">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold">Notifications</div>
            <button
              className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs hover:bg-white/10"
              onClick={() => {
                onMarkAllRead?.();
                setOpen(false);
              }}
            >
              Mark all read
            </button>
          </div>

          <div className="mt-3 space-y-2">
            {items.length === 0 ? (
              <div className="text-xs text-white/60">No notifications.</div>
            ) : (
              items.slice(0, 8).map((n) => (
                <div
                  key={n.id}
                  className="rounded-xl border border-white/10 bg-white/5 p-2"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="text-xs">
                      <div className={n.unread ? "font-semibold" : "text-white/80"}>
                        {n.text}
                      </div>
                      {n.time && <div className="mt-1 text-[11px] text-white/60">{n.time}</div>}
                    </div>
                    {n.unread && (
                      <span className="mt-0.5 inline-block h-2 w-2 rounded-full bg-red-500" />
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
