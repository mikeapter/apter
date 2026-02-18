"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "./NavItems";
import { COMPLIANCE } from "../../lib/compliance";

export function Sidebar({
  collapsed,
  onToggleCollapse,
  onNavigate,
}: {
  collapsed: boolean;
  onToggleCollapse: () => void;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();

  return (
    <aside
      className={[
        "h-full border-r bg-background",
        collapsed ? "w-16" : "w-56",
        "transition-[width] duration-200 ease-in-out",
      ].join(" ")}
    >
      <div className="h-14 px-3 flex items-center justify-end border-b">
        <button
          type="button"
          className="h-9 w-9 rounded border flex items-center justify-center"
          onClick={onToggleCollapse}
          aria-label="Toggle sidebar"
          title="Toggle sidebar"
        >
          {collapsed ? ">" : "<"}
        </button>
      </div>

      <nav className="p-2 space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={[
                "flex items-center gap-3 rounded px-3 py-2 border border-transparent",
                active
                  ? "bg-muted border-border"
                  : "hover:bg-muted/60",
              ].join(" ")}
              title={item.label}
            >
              <Icon size={18} />
              {!collapsed && (
                <span className="text-sm flex-1">{item.label}</span>
              )}
            </Link>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="absolute bottom-4 left-3 right-3">
          <div className="border rounded p-3 text-xs text-muted-foreground">
            {COMPLIANCE.NOT_INVESTMENT_ADVICE}
          </div>
        </div>
      )}
    </aside>
  );
}
