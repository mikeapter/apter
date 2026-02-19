"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "./NavItems";
import { COMPLIANCE } from "../../lib/compliance";

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <aside className="h-full w-56 border-r border-border bg-panel flex flex-col">
      {/* Logo + wordmark */}
      <div className="h-14 px-4 flex items-center gap-2.5 border-b border-border">
        <div className="h-8 w-8 rounded-full border border-border flex items-center justify-center bg-panel-2">
          <span className="text-[12px] font-bold tracking-[0.06em]">A</span>
        </div>
        <div className="leading-tight">
          <div className="text-[10px] text-muted-foreground tracking-[0.16em] uppercase">Apter</div>
          <div className="text-[12px] font-semibold tracking-tight">Financial</div>
        </div>
      </div>

      {/* Navigation — no collapse button, fixed width */}
      <nav className="flex-1 p-2 space-y-0.5 overflow-auto">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={[
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-muted/80 border border-border text-foreground"
                  : "border border-transparent text-muted-foreground hover:bg-muted/40 hover:text-foreground",
              ].join(" ")}
              title={item.label}
            >
              <Icon size={16} />
              <span className="flex-1">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Compliance notice */}
      <div className="p-3 border-t border-border">
        <div className="rounded-md border border-border bg-panel-2 p-2.5 text-[10px] text-muted-foreground leading-relaxed">
          {COMPLIANCE.NOT_INVESTMENT_ADVICE}
        </div>
      </div>
    </aside>
  );
}
