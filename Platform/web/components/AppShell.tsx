"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NotificationBell } from "./NotificationBell";

function ThemeToggleButton() {
  const [mounted, setMounted] = React.useState(false);
  const [theme, setTheme] = React.useState<"dark" | "light">("dark");

  React.useEffect(() => {
    setMounted(true);
    const current = document.documentElement.classList.contains("light")
      ? "light"
      : "dark";
    setTheme(current as any);
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.classList.remove("dark", "light");
    document.documentElement.classList.add(next);
    // next-themes will keep this consistent once mounted; this avoids button weirdness.
    localStorage.setItem("theme", next);
  }

  if (!mounted) return null;

  return (
    <button
      onClick={toggle}
      className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10"
    >
      {theme === "dark" ? "🌙 Dark" : "☀️ Light"}
    </button>
  );
}

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: "🏠" },
  { href: "/portfolio", label: "Portfolio", icon: "💼" },
  { href: "/bot-configuration", label: "Bot Configuration", icon: "🤖" },
  { href: "/trade-history", label: "Trade History", icon: "🧾" },
  { href: "/transfers", label: "Deposits & Withdrawals", icon: "🏦" },
  { href: "/watchlist", label: "Watchlist", icon: "👁️" },
  { href: "/market-data", label: "Market Data", icon: "📈" },
  { href: "/reports", label: "Reports & Analytics", icon: "📄" },
  { href: "/settings", label: "Settings", icon: "⚙️" },
  { href: "/support", label: "Help & Support", icon: "❓" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [accountOpen, setAccountOpen] = React.useState(false);

  React.useEffect(() => {
    setMobileOpen(false);
    setAccountOpen(false);
  }, [pathname]);

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Mobile overlay */}
      {mobileOpen && (
        <button
          className="fixed inset-0 z-30 bg-black/60"
          onClick={() => setMobileOpen(false)}
          aria-label="Close menu"
        />
      )}

      {/* Sidebar */}
      <aside
        className={[
          "fixed z-40 h-screen border-r border-white/10 bg-black/80 backdrop-blur",
          collapsed ? "w-20" : "w-64",
          "transition-all duration-200",
          "md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        ].join(" ")}
      >
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-white/10 flex items-center justify-center font-semibold">
              BT
            </div>
            {!collapsed && (
              <div>
                <div className="font-semibold">BotTrader</div>
                <div className="text-xs text-gray-400">Control Plane</div>
              </div>
            )}
          </div>
          <button
            className="hidden md:inline-flex rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs hover:bg-white/10"
            onClick={() => setCollapsed((v) => !v)}
            aria-label="Toggle sidebar"
          >
            {collapsed ? "➡️" : "⬅️"}
          </button>
        </div>

        <nav className="px-2 py-2 space-y-1">
          {nav.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={[
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm",
                  active ? "bg-white/10" : "hover:bg-white/5",
                ].join(" ")}
              >
                <span className="text-base">{item.icon}</span>
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-3 left-3 right-3 rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-gray-300">
          <div className="font-semibold text-white/90">Safety rule</div>
          <div>UI never trades. UI → API → Runtime → Bot.</div>
        </div>
      </aside>

      {/* Main */}
      <div className={collapsed ? "md:ml-20" : "md:ml-64"}>
        {/* Top bar */}
        <header className="sticky top-0 z-20 border-b border-white/10 bg-black/60 backdrop-blur">
          <div className="flex items-center justify-between gap-3 p-4">
            <div className="flex items-center gap-3">
              {/* Mobile hamburger */}
              <button
                className="md:hidden rounded-full border border-white/10 bg-white/5 px-3 py-2 hover:bg-white/10"
                onClick={() => setMobileOpen(true)}
                aria-label="Open menu"
              >
                ☰
              </button>
              <div className="text-lg font-semibold">BotTrader</div>
            </div>

            <div className="flex items-center gap-2">
              <div className="hidden md:block">
                <input
                  placeholder="Search..."
                  className="w-80 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm outline-none focus:bg-white/10"
                />
              </div>

              <ThemeToggleButton />
              <NotificationBell />

              {/* Account dropdown */}
              <div className="relative">
                <button
                  onClick={() => setAccountOpen((v) => !v)}
                  className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm hover:bg-white/10"
                >
                  <div className="h-7 w-7 rounded-full bg-white/10 flex items-center justify-center text-xs">
                    DU
                  </div>
                  <span className="hidden sm:inline">Account</span>
                  <span>▾</span>
                </button>

                {accountOpen && (
                  <>
                    <button
                      className="fixed inset-0 cursor-default"
                      onClick={() => setAccountOpen(false)}
                      aria-label="Close account menu"
                    />
                    <div className="absolute right-0 mt-2 w-48 rounded-xl border border-white/10 bg-black/90 backdrop-blur p-2 shadow-lg">
                      <Link
                        href="/profile"
                        className="block rounded-lg px-3 py-2 text-sm hover:bg-white/10"
                      >
                        Profile
                      </Link>
                      <Link
                        href="/settings"
                        className="block rounded-lg px-3 py-2 text-sm hover:bg-white/10"
                      >
                        Settings
                      </Link>
                      <button
                        className="w-full text-left rounded-lg px-3 py-2 text-sm hover:bg-white/10"
                        onClick={() => alert("Logout placeholder")}
                      >
                        Logout
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </header>

        <main className="p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
