"use client";

import * as React from "react";
import Link from "next/link";
import { Menu, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { getStoredUser, getToken, setStoredUser, logout as clearAuth } from "@/lib/auth";
import { apiGet } from "@/lib/api";
import type { StoredUser } from "@/lib/auth";
import Sidebar from "./Sidebar";
import MarketSearch from "@/app/components/market/MarketSearch";

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

    // Load user info from localStorage
    const token = getToken();
    setIsLoggedIn(!!token);
    const storedUser = getStoredUser();
    setUser(storedUser);

    // If logged in but no name data, fetch profile from API
    if (token && (!storedUser?.first_name && !storedUser?.full_name)) {
      apiGet<{ id: number; email: string; first_name: string; last_name: string; full_name: string }>(
        "/api/me",
        undefined,
        token
      ).then((res) => {
        if (res.ok) {
          const updated: StoredUser = {
            id: res.data.id,
            email: res.data.email,
            first_name: res.data.first_name,
            last_name: res.data.last_name,
            full_name: res.data.full_name,
          };
          setStoredUser(updated);
          setUser(updated);
        }
      }).catch(() => {
        // Silently ignore — greeting will use email fallback
      });
    }
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

  // Derive display name: prefer first_name, then full_name, then email prefix
  const displayName = user?.first_name
    || user?.full_name?.split(" ")[0]
    || user?.email?.split("@")[0]
    || "";

  const greeting = displayName
    ? `Welcome back, ${displayName}`
    : "Apter Financial";

  const initials = user
    ? (
        `${(user.first_name || user.full_name?.split(" ")[0] || "")[0] || ""}${(user.last_name || user.full_name?.split(" ").slice(1).join(" ") || "")[0] || ""}`.toUpperCase() || "U"
      )
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

          <div className="text-sm font-semibold tracking-wide shrink-0">{greeting}</div>

          <div className="hidden sm:flex flex-1 justify-center px-4">
            <MarketSearch />
          </div>

          <div className="ml-auto flex items-center gap-3 shrink-0">
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
