"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { LogOut, Settings, Shield, UserRound } from "lucide-react";

export default function UserMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!ref.current) return;
      if (!ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        className="bt-button gap-2"
        onClick={() => setOpen((v) => !v)}
        aria-label="Account menu"
      >
        <span className="h-7 w-7 rounded-md border border-border bg-panel-2 flex items-center justify-center text-xs font-semibold">
          DU
        </span>
        <span className="hidden sm:inline">Account</span>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-56 rounded-lg border border-border bg-panel shadow-none overflow-hidden">
          <div className="px-3 py-2 text-xs text-muted-foreground border-b border-border">
            Signed in
          </div>

          <Link
            href="/profile"
            className="flex items-center gap-2 px-3 py-2 hover:bg-muted text-sm"
            onClick={() => setOpen(false)}
          >
            <UserRound className="h-4 w-4" />
            Profile
          </Link>

          <Link
            href="/settings"
            className="flex items-center gap-2 px-3 py-2 hover:bg-muted text-sm"
            onClick={() => setOpen(false)}
          >
            <Settings className="h-4 w-4" />
            Settings
          </Link>

          <Link
            href="/security"
            className="flex items-center gap-2 px-3 py-2 hover:bg-muted text-sm"
            onClick={() => setOpen(false)}
          >
            <Shield className="h-4 w-4" />
            Security
          </Link>

          <div className="border-t border-border" />

          <Link
            href="/logout"
            className="flex items-center gap-2 px-3 py-2 hover:bg-muted text-sm text-risk-off"
            onClick={() => setOpen(false)}
          >
            <LogOut className="h-4 w-4" />
            Logout
          </Link>
        </div>
      )}
    </div>
  );
}
