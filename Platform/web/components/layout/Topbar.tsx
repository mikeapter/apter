"use client";

import { Bell, Menu, Search } from "lucide-react";
import UserMenu from "./UserMenu";

export default function Topbar({ onOpenMobile }: { onOpenMobile: () => void }) {
  return (
    <header className="sticky top-0 z-30 bg-panel border-b border-border h-16 flex items-center px-4 md:px-6 gap-3">
      {/* Mobile hamburger */}
      <button
        className="md:hidden p-2 rounded-md border border-border hover:bg-muted"
        onClick={onOpenMobile}
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="font-semibold">Dashboard</div>

      <div className="flex-1 max-w-xl">
        <div className="flex items-center gap-2 rounded-md border border-input bg-background px-3 py-2">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            className="w-full bg-transparent outline-none text-sm placeholder:text-muted-foreground"
            placeholder="Search"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          className="relative p-2 rounded-md border border-border hover:bg-muted"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute -top-1 -right-1 h-5 min-w-5 px-1 rounded-full bg-muted text-[11px] font-semibold flex items-center justify-center border border-border">
            2
          </span>
        </button>

        <UserMenu />
      </div>
    </header>
  );
}
