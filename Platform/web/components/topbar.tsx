"use client";

import * as React from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { NotificationBell } from "@/components/notification-bell";

export function Topbar({
  onOpenMobileMenu,
  activity = [],
}: {
  onOpenMobileMenu: () => void;
  activity?: { id: string; text: string; time?: string }[];
}) {
  const [accountOpen, setAccountOpen] = React.useState(false);

  const notifications = activity.map((a, idx) => ({
    id: a.id ?? String(idx),
    text: a.text,
    time: a.time,
    unread: idx < 2, // demo: treat top 2 as unread
  }));

  return (
    <div className="sticky top-0 z-40 w-full border-b border-white/10 bg-black/50 backdrop-blur">
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        {/* Left */}
        <div className="flex items-center gap-3">
          {/* Mobile hamburger */}
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-xl border border-white/10 bg-white/5 px-3 py-2 hover:bg-white/10 lg:hidden"
            onClick={onOpenMobileMenu}
            aria-label="Open menu"
          >
            ☰
          </button>

          <div className="hidden items-center gap-2 lg:flex">
            <div className="h-8 w-8 rounded-xl bg-white/10" />
            <div className="leading-tight">
              <div className="text-sm font-semibold">BotTrader</div>
              <div className="text-[11px] text-white/60">Control Plane</div>
            </div>
          </div>
        </div>

        {/* Center search */}
        <div className="flex-1">
          <div className="mx-auto max-w-xl">
            <input
              className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-2 text-sm outline-none placeholder:text-white/40 focus:border-white/20"
              placeholder="Search..."
            />
          </div>
        </div>

        {/* Right */}
        <div className="flex items-center gap-2">
          <ThemeToggle />

          <NotificationBell
            items={notifications}
            onMarkAllRead={() => {
              // optional: wire this later to real "read" state
            }}
          />

          {/* Account dropdown */}
          <div className="relative">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 hover:bg-white/10"
              onClick={() => setAccountOpen((v) => !v)}
              aria-label="Account menu"
            >
              {/* avatar */}
              <div className="h-7 w-7 rounded-full bg-white/15" />
              <span className="text-xs">Account</span>
              <span className="text-xs text-white/60">▾</span>
            </button>

            {accountOpen && (
              <div className="absolute right-0 z-50 mt-2 w-44 rounded-2xl border border-white/10 bg-black/90 p-2 shadow-xl backdrop-blur">
                <a className="block rounded-xl px-3 py-2 text-xs hover:bg-white/10" href="/profile">
                  Profile
                </a>
                <a className="block rounded-xl px-3 py-2 text-xs hover:bg-white/10" href="/settings">
                  Settings
                </a>
                <a className="block rounded-xl px-3 py-2 text-xs hover:bg-white/10" href="/logout">
                  Logout
                </a>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
