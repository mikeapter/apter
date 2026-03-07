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
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-border/60 bg-panel/80 backdrop-blur-xl pb-[env(safe-area-inset-bottom)]">
      <div className="flex items-center justify-around h-16">
        {MOBILE_NAV.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={[
                "relative flex flex-col items-center justify-center gap-1 min-w-[64px] min-h-[44px] py-1.5 px-3 rounded-xl transition-colors",
                active
                  ? "text-foreground"
                  : "text-muted-foreground active:text-foreground",
              ].join(" ")}
            >
              {active && (
                <span className="absolute -top-1 left-1/2 -translate-x-1/2 w-5 h-[3px] rounded-full bg-foreground" />
              )}
              <Icon size={20} strokeWidth={active ? 2 : 1.5} />
              <span className="text-[10px] leading-none font-medium">
                {item.label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
