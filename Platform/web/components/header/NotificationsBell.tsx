"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";

type NotificationItem = {
  id: string;
  title: string;
  body?: string;
  ts: string; // display string
  read: boolean;
};

function useClickOutside(ref: React.RefObject<HTMLElement>, onOutside: () => void) {
  useEffect(() => {
    function handler(e: MouseEvent) {
      const el = ref.current;
      if (!el) return;
      if (e.target instanceof Node && !el.contains(e.target)) onOutside();
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [ref, onOutside]);
}

export default function NotificationsBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([
    { id: "n1", title: "Dashboard connected", body: "API data loaded successfully.", ts: "now", read: false },
    { id: "n2", title: "Bot status", body: "Opening bot is currently Paused.", ts: "now", read: false },
  ]);

  const wrapperRef = useRef<HTMLDivElement>(null);
  useClickOutside(wrapperRef, () => setOpen(false));

  const unread = useMemo(() => items.filter((x) => !x.read).length, [items]);

  const markAllRead = () => setItems((prev) => prev.map((n) => ({ ...n, read: true })));
  const toggleRead = (id: string) =>
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, read: !n.read } : n)));

  return (
    <div className="relative" ref={wrapperRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 hover:bg-white/10"
        aria-label="Notifications"
      >
        <span className="text-sm">🔔</span>
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-red-600 px-1 text-xs font-semibold text-white">
            {unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 overflow-hidden rounded-xl border border-white/10 bg-black/90 shadow-xl backdrop-blur">
          <div className="flex items-center justify-between px-3 py-2">
            <div className="text-sm font-semibold text-white">Notifications</div>
            <button
              type="button"
              onClick={markAllRead}
              className="text-xs text-white/70 hover:text-white"
            >
              Mark all read
            </button>
          </div>

          <div className="max-h-80 overflow-auto">
            {items.length === 0 ? (
              <div className="px-3 py-6 text-sm text-white/60">No notifications</div>
            ) : (
              items.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => toggleRead(n.id)}
                  className="w-full border-t border-white/10 px-3 py-3 text-left hover:bg-white/5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white">{n.title}</span>
                        {!n.read && <span className="h-2 w-2 rounded-full bg-red-500" />}
                      </div>
                      {n.body && <div className="mt-1 text-xs text-white/60">{n.body}</div>}
                    </div>
                    <div className="text-[11px] text-white/50">{n.ts}</div>
                  </div>
                </button>
              ))
            )}
          </div>

          <div className="border-t border-white/10 px-3 py-2 text-xs text-white/50">
            Click an item to toggle read/unread.
          </div>
        </div>
      )}
    </div>
  );
}
