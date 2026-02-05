"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { useTheme } from "next-themes";
import { Bell, Menu, Moon, Sun, ChevronDown } from "lucide-react";

function useClickOutside(
  ref: React.RefObject<HTMLElement>,
  onOutside: () => void
) {
  React.useEffect(() => {
    function handler(e: MouseEvent) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target as Node)) onOutside();
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [ref, onOutside]);
}

export default function Header({
  onOpenMobile,
}: {
  onOpenMobile: () => void;
}) {
  const { theme, setTheme } = useTheme();
  const [notifOpen, setNotifOpen] = React.useState(false);
  const [acctOpen, setAcctOpen] = React.useState(false);

  const notifRef = React.useRef<HTMLDivElement>(null);
  const acctRef = React.useRef<HTMLDivElement>(null);
  useClickOutside(notifRef, () => setNotifOpen(false));
  useClickOutside(acctRef, () => setAcctOpen(false));

  // Fake user (replace later with real auth user)
  const user = {
    name: "Demo User",
    initials: "DU",
    // set to null to test fallback:
    avatarUrl: null as string | null,
  };

  const notifications = [
    { id: "n1", title: "Bot paused", body: "Opening bot is paused.", time: "now" },
    { id: "n2", title: "Market closed", body: "US equities are closed.", time: "1h" },
  ];

  const unreadCount = notifications.length;

  return (
    <header className="sticky top-0 z-20 bg-black/30 backdrop-blur border-b border-white/10">
      <div className="h-16 px-4 flex items-center gap-3">
        {/* Mobile hamburger */}
        <button
          className="md:hidden w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 grid place-items-center"
          onClick={onOpenMobile}
          aria-label="Open menu"
        >
          <Menu size={18} />
        </button>

        <div className="text-sm font-semibold hidden md:block">Dashboard</div>

        {/* Search */}
        <div className="flex-1">
          <input
            placeholder="Search…"
            className="w-full max-w-[640px] bg-white/5 border border-white/10 rounded-2xl px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-white/10"
          />
        </div>

        {/* Theme toggle */}
        <button
          className="h-10 px-3 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-sm inline-flex items-center gap-2"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label="Toggle theme"
          title="Toggle theme"
        >
          {theme === "dark" ? <Moon size={16} /> : <Sun size={16} />}
          <span className="hidden sm:inline">{theme === "dark" ? "Dark" : "Light"}</span>
        </button>

        {/* Notifications */}
        <div className="relative" ref={notifRef}>
          <button
            className="w-10 h-10 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 grid place-items-center relative"
            onClick={() => setNotifOpen((v) => !v)}
            aria-label="Notifications"
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 text-[10px] rounded-full bg-red-500 text-white px-1.5 py-0.5">
                {unreadCount}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 mt-2 w-[320px] rounded-2xl border border-white/10 bg-black/80 backdrop-blur shadow-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-white/10">
                <div className="text-sm font-semibold">Notifications</div>
                <div className="text-xs text-white/60">{unreadCount} unread</div>
              </div>
              <div className="max-h-[320px] overflow-auto">
                {notifications.map((n) => (
                  <div key={n.id} className="px-4 py-3 border-b border-white/5 hover:bg-white/5">
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-semibold">{n.title}</div>
                      <div className="text-xs text-white/50">{n.time}</div>
                    </div>
                    <div className="text-xs text-white/60 mt-1">{n.body}</div>
                  </div>
                ))}
              </div>
              <div className="px-4 py-3">
                <button
                  className="w-full rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-sm py-2"
                  onClick={() => setNotifOpen(false)}
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Account dropdown */}
        <div className="relative" ref={acctRef}>
          <button
            className="h-10 px-2 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 inline-flex items-center gap-2"
            onClick={() => setAcctOpen((v) => !v)}
            aria-label="Account menu"
          >
            <div className="w-8 h-8 rounded-full bg-white/10 overflow-hidden grid place-items-center">
              {user.avatarUrl ? (
                <Image
                  src={user.avatarUrl}
                  alt="User avatar"
                  width={32}
                  height={32}
                />
              ) : (
                <span className="text-xs font-semibold">{user.initials}</span>
              )}
            </div>
            <span className="text-sm hidden sm:inline">Account</span>
            <ChevronDown size={16} className="text-white/70" />
          </button>

          {acctOpen && (
            <div className="absolute right-0 mt-2 w-[220px] rounded-2xl border border-white/10 bg-black/80 backdrop-blur shadow-xl overflow-hidden">
              <Link
                href="/profile"
                className="block px-4 py-3 text-sm hover:bg-white/5"
                onClick={() => setAcctOpen(false)}
              >
                Profile
              </Link>
              <Link
                href="/settings"
                className="block px-4 py-3 text-sm hover:bg-white/5"
                onClick={() => setAcctOpen(false)}
              >
                Settings
              </Link>
              <button
                className="w-full text-left px-4 py-3 text-sm hover:bg-white/5"
                onClick={() => {
                  setAcctOpen(false);
                  alert("Logout is stubbed for now (wire auth later).");
                }}
              >
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
