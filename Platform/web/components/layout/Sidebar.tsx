"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  PieChart,
  SlidersHorizontal,
  History,
  ArrowLeftRight,
  Eye,
  LineChart,
  BarChart3,
  Settings,
  HelpCircle,
  CreditCard,
  X,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";

export type SidebarProps = {
  collapsed?: boolean;
  onToggleCollapsed?: () => void;

  /**
   * When true, Sidebar renders as a mobile overlay drawer.
   * Parent controls when it appears (e.g., only render when open).
   */
  isMobile?: boolean;
  onCloseMobile?: () => void;

  className?: string;
};

type NavItem = {
  href: string;
  label: string;
  Icon: LucideIcon;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { href: "/portfolio", label: "Portfolio", Icon: PieChart },
  { href: "/bot-configuration", label: "Bot Configuration", Icon: SlidersHorizontal },
  { href: "/trade-history", label: "Trade History", Icon: History },
  { href: "/deposits-withdrawals", label: "Deposits & Withdrawals", Icon: ArrowLeftRight },
  { href: "/watchlist", label: "Watchlist", Icon: Eye },
  { href: "/market-data", label: "Market Data", Icon: LineChart },
  { href: "/reports-analytics", label: "Reports & Analytics", Icon: BarChart3 },
  { href: "/plans", label: "Plans", Icon: CreditCard },
  { href: "/settings", label: "Settings", Icon: Settings },
  { href: "/help-support", label: "Help & Support", Icon: HelpCircle },
];

export function Sidebar({
  collapsed = false,
  onToggleCollapsed,
  isMobile = false,
  onCloseMobile,
  className,
}: SidebarProps) {
  const pathname = usePathname() || "";

  const rail = (
    <aside
      className={cn(
        "h-full bg-[#06102E] text-slate-100 border-r border-white/10",
        collapsed ? "w-16" : "w-64",
        className
      )}
      aria-label="Primary"
    >
      {/* Header */}
      <div
        className={cn(
          "flex h-14 items-center gap-3 border-b border-white/10 px-3",
          collapsed ? "justify-center" : ""
        )}
      >
        <div className={cn("flex items-center gap-2 min-w-0", collapsed ? "justify-center" : "")}>
          <div className="h-8 w-8 rounded-md bg-white/10 flex items-center justify-center text-xs font-semibold">
            A
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <div className="text-sm font-semibold tracking-wide leading-none">Apter</div>
              <div className="text-[11px] text-white/60 leading-none mt-1">Signals Only</div>
            </div>
          )}
        </div>

        {/* Desktop collapse control */}
        {!isMobile && onToggleCollapsed && (
          <button
            type="button"
            onClick={onToggleCollapsed}
            className={cn(
              "ml-auto inline-flex h-9 w-9 items-center justify-center rounded-md border border-white/10 bg-white/5 hover:bg-white/10",
              collapsed ? "ml-0" : ""
            )}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            title={collapsed ? "Expand" : "Collapse"}
          >
            {collapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
          </button>
        )}

        {/* Mobile close control */}
        {isMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            className="ml-auto inline-flex h-9 w-9 items-center justify-center rounded-md border border-white/10 bg-white/5 hover:bg-white/10"
            aria-label="Close menu"
            title="Close"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="p-2">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.Icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={isMobile ? onCloseMobile : undefined}
              className={cn(
                "group flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                collapsed ? "justify-center" : "",
                active
                  ? "bg-white/10 text-white"
                  : "text-white/80 hover:bg-white/10 hover:text-white"
              )}
              aria-current={active ? "page" : undefined}
              title={collapsed ? item.label : undefined}
            >
              <Icon className={cn("h-5 w-5 shrink-0", active ? "text-white" : "text-white/70 group-hover:text-white")} />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="mt-auto px-3 py-3 text-[11px] text-white/50 border-t border-white/10">
          Institutional dashboard • calm UI • no gamification
        </div>
      )}
    </aside>
  );

  // Mobile overlay drawer
  if (isMobile) {
    return (
      <div className="fixed inset-0 z-50 lg:hidden">
        <div className="absolute inset-0 bg-black/60" onClick={onCloseMobile} />
        <div className="absolute left-0 top-0 h-full">{rail}</div>
      </div>
    );
  }

  // Desktop sticky rail
  return <div className="sticky top-0 h-screen">{rail}</div>;
}

export default Sidebar;
