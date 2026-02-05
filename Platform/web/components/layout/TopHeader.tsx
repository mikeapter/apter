"use client";

import * as React from "react";
import Link from "next/link";
import { Bell, ChevronDown, Menu, Search, User } from "lucide-react";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { cn } from "@/lib/utils";

type Notification = {
  id: string;
  title: string;
  time: string;
  unread?: boolean;
};

const MOCK_NOTIFICATIONS: Notification[] = [
  { id: "n1", title: "Bot paused (manual)", time: "2m", unread: true },
  { id: "n2", title: "New trade executed", time: "35m", unread: true },
  { id: "n3", title: "Daily report ready", time: "3h" }
];

type Props = {
  onOpenMobileNav: () => void;
};

function useOutsideClose<T extends HTMLElement>(open: boolean, onClose: () => void) {
  const ref = React.useRef<T | null>(null);

  React.useEffect(() => {
    if (!open) return;

    function handle(event: MouseEvent | TouchEvent) {
      const el = ref.current;
      if (!el) return;
      if (event.target instanceof Node && !el.contains(event.target)) {
        onClose();
      }
    }

    document.addEventListener("mousedown", handle);
    document.addEventListener("touchstart", handle);
    return () => {
      document.removeEventListener("mousedown", handle);
      document.removeEventListener("touchstart", handle);
    };
  }, [open, onClose]);

  return ref;
}

export function TopHeader({ onOpenMobileNav }: Props) {
  const [notifOpen, setNotifOpen] = React.useState(false);
  const [userOpen, setUserOpen] = React.useState(false);

  const unreadCount = React.useMemo(
    () => MOCK_NOTIFICATIONS.filter((n) => n.unread).length,
    []
  );

  const notifRef = useOutsideClose<HTMLDivElement>(notifOpen, () => setNotifOpen(false));
  const userRef = useOutsideClose<HTMLDivElement>(userOpen, () => setUserOpen(false));

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-zinc-200 bg-white/80 px-4 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <button
        type="button"
        className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-zinc-200 bg-white text-zinc-900 shadow-sm transition hover:bg-zinc-50 md:hidden dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-100 dark:hover:bg-zinc-900"
        aria-label="Open navigation"
        onClick={onOpenMobileNav}
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="hidden items-center gap-2 md:flex">
        <div className="text-sm font-semibold">Dashboard</div>
      </div>

      <div className="ml-auto flex items-center gap-2">
        <div className="hidden items-center gap-2 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-700 shadow-sm md:flex dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-200">
          <Search className="h-4 w-4" />
          <input
            className="w-56 bg-transparent outline-none placeholder:text-zinc-400"
            placeholder="Search…"
            aria-label="Search"
          />
        </div>

        <ThemeToggle />

        <div className="relative" ref={notifRef}>
          <button
            type="button"
            className="relative inline-flex h-10 w-10 items-center justify-center rounded-xl border border-zinc-200 bg-white text-zinc-900 shadow-sm transition hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-100 dark:hover:bg-zinc-900"
            aria-label="Notifications"
            onClick={() => setNotifOpen((v) => !v)}
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-xs font-semibold text-white">
                {unreadCount}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="absolute right-0 mt-2 w-72 rounded-2xl border border-zinc-200 bg-white p-2 shadow-lg dark:border-zinc-800 dark:bg-zinc-950">
              <div className="px-2 py-1 text-xs font-semibold text-zinc-500 dark:text-zinc-400">
                Notifications
              </div>
              <ul className="space-y-1">
                {MOCK_NOTIFICATIONS.map((n) => (
                  <li key={n.id}>
                    <button
                      type="button"
                      className={cn(
                        "w-full rounded-xl px-2 py-2 text-left text-sm transition hover:bg-zinc-100 dark:hover:bg-zinc-900",
                        n.unread ? "bg-zinc-50 dark:bg-zinc-900/40" : ""
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-zinc-900 dark:text-zinc-100">{n.title}</span>
                        <span className="text-xs text-zinc-500 dark:text-zinc-400">{n.time}</span>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
              <div className="mt-2 px-2">
                <Link
                  href="/reports"
                  className="text-xs text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-300"
                >
                  View all
                </Link>
              </div>
            </div>
          )}
        </div>

        <div className="relative" ref={userRef}>
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-2 py-1.5 text-sm text-zinc-900 shadow-sm transition hover:bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-100 dark:hover:bg-zinc-900"
            aria-label="User menu"
            onClick={() => setUserOpen((v) => !v)}
          >
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-xl bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200">
              <User className="h-4 w-4" />
            </span>
            <span className="hidden sm:inline">Account</span>
            <ChevronDown className="h-4 w-4" />
          </button>

          {userOpen && (
            <div className="absolute right-0 mt-2 w-48 rounded-2xl border border-zinc-200 bg-white p-2 shadow-lg dark:border-zinc-800 dark:bg-zinc-950">
              <Link
                href="/settings"
                className="block rounded-xl px-2 py-2 text-sm text-zinc-800 transition hover:bg-zinc-100 dark:text-zinc-200 dark:hover:bg-zinc-900"
              >
                Profile
              </Link>
              <Link
                href="/settings"
                className="block rounded-xl px-2 py-2 text-sm text-zinc-800 transition hover:bg-zinc-100 dark:text-zinc-200 dark:hover:bg-zinc-900"
              >
                Settings
              </Link>
              <div className="my-1 h-px bg-zinc-200 dark:bg-zinc-800" />
              <Link
                href="/logout"
                className="block rounded-xl px-2 py-2 text-sm text-zinc-800 transition hover:bg-zinc-100 dark:text-zinc-200 dark:hover:bg-zinc-900"
              >
                Logout
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
