"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, User, Settings, CreditCard, LogOut } from "lucide-react";
import { COMPLIANCE } from "../../lib/compliance";

function DisclosureBanner() {
  return (
    <div className="w-full border-b border-border bg-panel-2 px-4 py-2">
      <p className="text-[11px] md:text-xs text-muted-foreground tracking-[0.01em]">
        {COMPLIANCE.DISCLOSURE_BANNER}
      </p>
    </div>
  );
}

function BrandMark() {
  return (
    <div className="h-8 w-8 rounded-full border border-border flex items-center justify-center">
      <span className="text-[12px] font-semibold tracking-[0.06em]">A</span>
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

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="h-9 w-9 rounded-full border border-border flex items-center justify-center hover:bg-muted"
        aria-label="User menu"
      >
        <User size={16} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-48 rounded-md border border-border bg-card shadow-lg z-50">
          <nav className="py-1">
            <a
              href="/profile"
              className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted"
              onClick={() => setOpen(false)}
            >
              <User size={14} />
              Profile
            </a>
            <a
              href="/settings"
              className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted"
              onClick={() => setOpen(false)}
            >
              <Settings size={14} />
              Settings
            </a>
            <a
              href="/plans"
              className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted"
              onClick={() => setOpen(false)}
            >
              <CreditCard size={14} />
              Subscription
            </a>
            <div className="border-t border-border my-1" />
            <a
              href="/logout"
              className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-muted text-risk-off"
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
  return (
    <>
      <DisclosureBanner />

      <header className="h-14 border-b border-border bg-panel px-4 flex items-center justify-between gap-3">
        {/* Left: mobile menu + logo */}
        <div className="flex items-center gap-3 min-w-[180px]">
          <button
            type="button"
            className="md:hidden h-9 w-9 rounded border border-border flex items-center justify-center"
            onClick={onOpenMobile}
            aria-label="Open menu"
          >
            ☰
          </button>

          <div className="flex items-center gap-2">
            <BrandMark />
            <div className="leading-tight">
              <div className="text-xs text-muted-foreground tracking-[0.12em]">APTER</div>
              <div className="text-[12px] font-semibold tracking-tight">Financial</div>
            </div>
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
