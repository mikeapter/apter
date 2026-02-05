"use client";

import { useMemo, useState } from "react";

type NotificationItem = {
  id: string;
  title: string;
  body: string;
  time: string;
  unread: boolean;
};

export default function NotificationsPanel() {
  const [open, setOpen] = useState(false);

  const items: NotificationItem[] = useMemo(
    () => [
      { id: "n1", title: "Bot status", body: "Opening bot is Paused.", time: "now", unread: true },
      { id: "n2", title: "Market", body: "US Equities are Closed.", time: "5m", unread: true },
      { id: "n3", title: "System", body: "Dashboard endpoint online.", time: "1h", unread: false },
    ],
    []
  );

  const unreadCount = items.filter((x) => x.unread).length;

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative inline-flex items-center justify-center rounded-xl border px-3 py-2 text-sm hover:bg-muted"
        aria-label="Notifications"
      >
        <span className="mr-2">🔔</span>
        <span className="hidden sm:inline">Notifications</span>

        {unreadCount > 0 && (
          <span className="absolute -right-2 -top-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-xs font-semibold text-white">
            {unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-[340px] rounded-2xl border bg-background shadow-xl">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="text-sm font-semibold">Notifications</div>
            <button
              type="button"
              className="rounded-lg px-2 py-1 text-xs hover:bg-muted"
              onClick={() => setOpen(false)}
            >
              Close
            </button>
          </div>

          <div className="max-h-[360px] overflow-auto px-2 pb-2">
            {items.map((n) => (
              <div
                key={n.id}
                className="mb-2 rounded-xl border p-3 hover:bg-muted"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="text-sm font-medium">
                    {n.title}{" "}
                    {n.unread && <span className="ml-1 text-xs text-red-500">●</span>}
                  </div>
                  <div className="text-xs text-muted-foreground">{n.time}</div>
                </div>
                <div className="mt-1 text-sm text-muted-foreground">{n.body}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
