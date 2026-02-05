"use client";

import * as React from "react";

type Notice = { id: string; title: string; time: string; unread?: boolean };

const seed: Notice[] = [
  { id: "n1", title: "Dashboard endpoint online", time: "now", unread: true },
  { id: "n2", title: "Bot status changed: Paused", time: "5m", unread: true },
  { id: "n3", title: "Market status: Closed", time: "1h" },
];

export function NotificationBell() {
  const [open, setOpen] = React.useState(false);
  const [items, setItems] = React.useState<Notice[]>(seed);

  const unreadCount = items.filter((x) => x.unread).length;

  React.useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  function markAllRead() {
    setItems((prev) => prev.map((x) => ({ ...x, unread: false })));
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative inline-flex items-center justify-center rounded-full border border-white/10 bg-white/5 px-3 py-2 hover:bg-white/10"
        aria-label="Notifications"
      >
        <span className="text-sm">🔔</span>
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 rounded-full bg-red-600 px-2 py-0.5 text-xs">
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <button
            className="fixed inset-0 cursor-default"
            onClick={() => setOpen(false)}
            aria-label="Close notifications"
          />
          <div className="absolute right-0 mt-2 w-80 rounded-xl border border-white/10 bg-black/90 backdrop-blur p-3 shadow-lg">
            <div className="flex items-center justify-between pb-2">
              <div className="text-sm font-semibold">Notifications</div>
              <button
                onClick={markAllRead}
                className="text-xs text-gray-300 hover:text-white"
              >
                Mark all read
              </button>
            </div>

            <div className="max-h-72 overflow-auto space-y-2">
              {items.map((n) => (
                <div
                  key={n.id}
                  className={`rounded-lg border border-white/10 p-3 ${
                    n.unread ? "bg-white/10" : "bg-white/5"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="text-sm">{n.title}</div>
                    <div className="text-xs text-gray-400">{n.time}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
