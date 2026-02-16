"use client";

import * as React from "react";
import Link from "next/link";
import { Menu, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { getStoredUser, getToken, logout as clearAuth } from "@/lib/auth";
import type { StoredUser } from "@/lib/auth";
import Sidebar from "./Sidebar";

export type AppShellProps = {
  children: React.ReactNode;
  className?: string;
};

function useIsMobile(breakpointPx: number = 1024) {
  const [isMobile, setIsMobile] = React.useState(false);

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${breakpointPx - 1}px)`);
    const update = () => setIsMobile(mql.matches);
    update();

    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", update);
      return () => mql.removeEventListener("change", update);
    }

    const legacy = mql as MediaQueryList & {
      addListener?: (listener: () => void) => void;
      removeListener?: (listener: () => void) => void;
    };

    if (typeof legacy.addListener === "function") {
      legacy.addListener(update);
      return () => {
        if (typeof legacy.removeListener === "function") legacy.removeListener(update);
      };
    }

    return;
  }, [breakpointPx]);

  return isMobile;
}

const STORAGE_KEY = "apter_sidebar_collapsed_v1";

export default function AppShell({ children, className }: AppShellProps) {
  const isMobile = useIsMobile();
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [collapsed, setCollapsed] = React.useState(false);
  const [user, setUser] = React.useState<StoredUser | null>(null);
  const [isLoggedIn, setIsLoggedIn] = React.useState(false);

  React.useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw === "1") setCollapsed(true);
    } catch {}

    // Load user info
    const token = getToken();
    setIsLoggedIn(!!token);
    setUser(getStoredUser());
  }, []);

  React.useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
    } catch {}
  }, [collapsed]);

  React.useEffect(() => {
    if (!isMobile) setMobileOpen(false);
  }, [isMobile]);

  function handleLogout() {
    clearAuth();
    window.location.href = "/";
  }

  const greeting = user?.first_name
    ? `Welcome back, ${user.first_name}`
    : "Apter Financial";

  const initials = user
    ? `${(user.first_name || "")[0] || ""}${(user.last_name || "")[0] || ""}`.toUpperCase() || "U"
    : "U";

  return (
    <div className={cn("flex min-h-screen w-full bg-background text-foreground", className)}>
      {!isMobile && (
        <Sidebar collapsed={collapsed} onToggleCollapsed={() => setCollapsed((v) => !v)} />
      )}

      {isMobile && mobileOpen && <Sidebar isMobile onCloseMobile={() => setMobileOpen(false)} />}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b border-white/10 bg-background/90 backdrop-blur px-4">
          {isMobile && (
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-white/10 bg-white/5"
              aria-label="Open menu"
              title="Menu"
            >
              <Menu className="h-5 w-5" />
            </button>
          )}

          <div className="text-sm font-semibold tracking-wide">{greeting}</div>

          <div className="ml-auto flex items-center gap-3">
            <div className="hidden sm:block text-xs text-white/60">Signals Only</div>
            {isLoggedIn ? (
              <>
                <div
                  className="h-8 w-8 rounded-full bg-white/10 flex items-center justify-center text-xs font-semibold"
                  aria-label="User avatar"
                >
                  {initials}
                </div>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex h-8 items-center gap-1.5 rounded-md border border-white/10 bg-white/5 px-2 text-xs text-white/70 hover:text-white hover:bg-white/10 transition-colors"
                  title="Sign out"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Sign out</span>
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="inline-flex h-8 items-center rounded-md border border-white/10 bg-white/5 px-3 text-xs text-white/70 hover:text-white hover:bg-white/10 transition-colors"
              >
                Sign in
              </Link>
            )}
          </div>
        </header>

        <main className="flex-1 min-w-0 p-4">{children}</main>
      </div>
    </div>
  );
}
