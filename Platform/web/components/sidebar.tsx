"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";
import {
  LayoutDashboard,
  Briefcase,
  Bot,
  History,
  Banknote,
  Eye,
  LineChart,
  FileText,
  Settings,
  HelpCircle,
  ChevronLeft,
} from "lucide-react";

type NavItem = {
  label: string;
  href: string;
  icon: React.ReactNode;
};

const NAV: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: <LayoutDashboard size={18} /> },
  { label: "Portfolio", href: "/portfolio", icon: <Briefcase size={18} /> },
  { label: "Bot Configuration", href: "/bot-configuration", icon: <Bot size={18} /> },
  { label: "Trade History", href: "/trade-history", icon: <History size={18} /> },
  { label: "Deposits & Withdrawals", href: "/transfers", icon: <Banknote size={18} /> },
  { label: "Watchlist", href: "/watchlist", icon: <Eye size={18} /> },
  { label: "Market Data", href: "/market-data", icon: <LineChart size={18} /> },
  { label: "Reports & Analytics", href: "/reports", icon: <FileText size={18} /> },
  { label: "Settings", href: "/settings", icon: <Settings size={18} /> },
  { label: "Help & Support", href: "/support", icon: <HelpCircle size={18} /> },
];

export default function Sidebar({
  collapsed,
  setCollapsed,
  mobileOpen,
  setMobileOpen,
}: {
  collapsed: boolean;
  setCollapsed: (v: boolean) => void;
  mobileOpen: boolean;
  setMobileOpen: (v: boolean) => void;
}) {
  const pathname = usePathname();

  const base =
    "h-full bg-black/40 backdrop-blur border-r border-white/10 flex flex-col";
  const width = collapsed ? "w-[76px]" : "w-[260px]";

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <button
          aria-label="Close sidebar overlay"
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={[
          "fixed z-50 md:static md:z-auto top-0 left-0",
          base,
          width,
          "transition-all duration-200",
          mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
        ].join(" ")}
      >
        {/* Brand */}
        <div className="h-16 flex items-center gap-3 px-4 border-b border-white/10">
          <div className="w-9 h-9 rounded-full bg-white/10 grid place-items-center text-sm font-semibold">
            BT
          </div>
          {!collapsed && (
            <div className="leading-tight">
              <div className="text-sm font-semibold">BotTrader</div>
              <div className="text-xs text-white/60">Control Plane</div>
            </div>
          )}

          <div className="ml-auto flex items-center gap-2">
            <button
              className="hidden md:inline-flex w-9 h-9 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 items-center justify-center"
              onClick={() => setCollapsed(!collapsed)}
              aria-label="Toggle sidebar collapse"
              title="Collapse sidebar"
            >
              <ChevronLeft
                size={18}
                className={collapsed ? "rotate-180 transition" : "transition"}
              />
            </button>

            <button
              className="md:hidden w-9 h-9 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10"
              onClick={() => setMobileOpen(false)}
              aria-label="Close sidebar"
              title="Close"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-2 space-y-1">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={[
                  "flex items-center gap-3 rounded-xl px-3 py-2 border border-transparent",
                  active
                    ? "bg-white/10 border-white/10"
                    : "hover:bg-white/5",
                ].join(" ")}
              >
                <span className="text-white/80">{item.icon}</span>
                {!collapsed && <span className="text-sm">{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Safety rule */}
        <div className="p-3 border-t border-white/10">
          <div className="rounded-xl bg-white/5 border border-white/10 p-3">
            <div className="text-xs text-white/70 font-semibold mb-1">
              Safety rule
            </div>
            <div className="text-xs text-white/60">
              UI never trades. UI → API → Runtime → Bot.
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
