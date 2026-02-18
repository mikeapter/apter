"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Briefcase, Eye, LineChart, Settings } from "lucide-react";

const MOBILE_NAV = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Portfolio", href: "/portfolio", icon: Briefcase },
  { label: "Watchlist", href: "/watchlist", icon: Eye },
  { label: "Market", href: "/market-data", icon: LineChart },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function MobileBottomNav() {
  const pathname = usePathname();

  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-panel pb-[env(safe-area-inset-bottom)]">
      <div className="flex items-center justify-around h-14">
        {MOBILE_NAV.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "flex flex-col items-center gap-0.5 py-1 px-2 rounded-md min-w-[56px] transition-colors",
                active ? "text-foreground" : "text-muted-foreground",
              ].join(" ")}
            >
              <Icon size={18} />
              <span className="text-[9px]">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
