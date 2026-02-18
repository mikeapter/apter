"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, User, Settings, CreditCard, LogOut, ChevronDown } from "lucide-react";
import { COMPLIANCE } from "../../lib/compliance";
import { useAuth } from "../../hooks/useAuth";

function DisclosureBanner() {
  return (
    <div className="w-full border-b border-border bg-panel-2 px-4 py-1.5">
      <p className="text-[10px] md:text-[11px] text-muted-foreground tracking-[0.01em] leading-relaxed">
        {COMPLIANCE.DISCLOSURE_BANNER}
      </p>
    </div>
  );
}

function StockSearch() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const ticker = query.trim().toUpperCase();
    if (ticker) {
      router.push(`/stocks/${ticker}`);
      setQuery("");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-md">
      <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search ticker or company..."
        className="w-full h-9 rounded-md border border-border bg-background pl-9 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring/40 placeholder:text-muted-foreground"
      />
    </form>
  );
}

function UserMenu() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const displayName = user?.email?.split("@")[0] || "User";

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 h-9 px-2 rounded-md border border-border hover:bg-muted/60 transition-colors"
        aria-label="User menu"
      >
        <div className="h-7 w-7 rounded-full border border-border bg-panel-2 flex items-center justify-center">
          <User size={14} />
        </div>
        <span className="hidden sm:block text-xs text-muted-foreground max-w-[120px] truncate">
          {displayName}
        </span>
        <ChevronDown size={12} className="text-muted-foreground" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-52 rounded-md border border-border bg-card shadow-lg z-50">
          <div className="px-3 py-2 border-b border-border">
            <div className="text-xs font-medium truncate">{displayName}</div>
            <div className="text-[10px] text-muted-foreground truncate">{user?.email}</div>
          </div>
          <nav className="py-1">
            <a
              href="/profile"
              className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
              onClick={() => setOpen(false)}
            >
              <User size={14} />
              Profile
            </a>
            <a
              href="/settings"
              className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
              onClick={() => setOpen(false)}
            >
              <Settings size={14} />
              Settings
            </a>
            <a
              href="/plans"
              className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
              onClick={() => setOpen(false)}
            >
              <CreditCard size={14} />
              Subscription
            </a>
            <div className="border-t border-border my-1" />
            <a
              href="/logout"
              className="flex items-center gap-2 px-3 py-2 text-sm text-risk-off hover:bg-muted/40 transition-colors"
              onClick={() => setOpen(false)}
            >
              <LogOut size={14} />
              Log Out
            </a>
          </nav>
        </div>
      )}
    </div>
  );
}

export function Topbar({ onOpenMobile }: { onOpenMobile: () => void }) {
  const { user } = useAuth();
  const firstName = user?.email?.split("@")[0] || "there";

  return (
    <>
      <DisclosureBanner />

      <header className="h-14 border-b border-border bg-panel px-4 flex items-center justify-between gap-3">
        {/* Left: mobile menu + welcome */}
        <div className="flex items-center gap-3 min-w-[180px]">
          <button
            type="button"
            className="lg:hidden h-9 w-9 rounded-md border border-border flex items-center justify-center hover:bg-muted/60"
            onClick={onOpenMobile}
            aria-label="Open menu"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <line x1="2" y1="4" x2="14" y2="4" />
              <line x1="2" y1="8" x2="14" y2="8" />
              <line x1="2" y1="12" x2="14" y2="12" />
            </svg>
          </button>

          <div className="hidden md:block">
            <span className="text-sm text-muted-foreground">Welcome back, </span>
            <span className="text-sm font-medium">{firstName}</span>
          </div>
        </div>

        {/* Center: stock search */}
        <div className="hidden sm:flex flex-1 justify-center max-w-lg">
          <StockSearch />
        </div>

        {/* Right: user menu */}
        <div className="flex items-center gap-2 justify-end min-w-[60px]">
          <UserMenu />
        </div>
      </header>
    </>
  );
}
