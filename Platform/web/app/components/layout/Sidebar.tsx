"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Lock } from "lucide-react";
import { NAV_ITEMS } from "./NavItems";
import { useAuth } from "../../hooks/useAuth";
import { tierAtLeast } from "@/lib/tiers";

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
  const { user } = useAuth();
  const userTier = user?.tier ?? "observer";

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
            A
          </div>
          {!collapsed && (
            <div className="leading-tight">
              <div className="font-semibold">Apter</div>
              <div className="text-xs text-muted-foreground">Financial</div>
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
          const locked = item.minTier
            ? !tierAtLeast(userTier, item.minTier)
            : false;

          return (
            <Link
              key={item.href}
              href={locked ? "/plans" : item.href}
              onClick={onNavigate}
              className={[
                "flex items-center gap-3 rounded px-3 py-2 border border-transparent",
                locked
                  ? "opacity-40 cursor-default"
                  : active
                  ? "bg-muted border-border"
                  : "hover:bg-muted/60",
              ].join(" ")}
              title={
                locked
                  ? `Upgrade to ${item.minTier} to access ${item.label}`
                  : item.label
              }
            >
              <Icon size={18} />
              {!collapsed && (
                <span className="text-sm flex-1">{item.label}</span>
              )}
              {!collapsed && locked && <Lock size={14} className="text-muted-foreground" />}
            </Link>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="absolute bottom-4 left-3 right-3">
          <div className="border rounded p-3 text-xs text-muted-foreground">
            <div className="font-semibold mb-1 text-foreground">Safety rule</div>
            UI never trades. UI provides analysis only.
          </div>
        </div>
      )}
    </aside>
  );
}
