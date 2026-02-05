"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "./NavItems";

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
        collapsed ? "w-16" : "w-64",
        "transition-[width] duration-200 ease-in-out",
      ].join(" ")}
    >
      <div className="h-14 px-3 flex items-center justify-between border-b">
        <div className="flex items-center gap-2 overflow-hidden">
          <div className="h-9 w-9 rounded-full border flex items-center justify-center font-bold">
            BT
          </div>
          {!collapsed && (
            <div className="leading-tight">
              <div className="font-semibold">BotTrader</div>
              <div className="text-xs text-muted-foreground">Control Plane</div>
            </div>
          )}
        </div>

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
                active ? "bg-muted border-border" : "hover:bg-muted/60",
              ].join(" ")}
              title={item.label}
            >
              <Icon size={18} />
              {!collapsed && <span className="text-sm">{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="absolute bottom-4 left-3 right-3">
          <div className="border rounded p-3 text-xs text-muted-foreground">
            <div className="font-semibold mb-1 text-foreground">Safety rule</div>
            UI never trades. UI → API → Runtime → Bot.
          </div>
        </div>
      )}
    </aside>
  );
}
