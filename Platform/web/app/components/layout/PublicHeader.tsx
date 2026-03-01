"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getToken } from "@/lib/auth";

function BrandMark() {
  return (
    <div className="h-8 w-8 rounded-full border border-border flex items-center justify-center">
      <span className="text-[12px] font-semibold tracking-[0.06em]">A</span>
    </div>
  );
}

export function PublicHeader() {
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    setHasToken(!!getToken());
  }, []);

  return (
    <header className="h-14 border-b border-border bg-panel px-4 flex items-center justify-between">
      <Link href="/" className="flex items-center gap-2">
        <BrandMark />
        <div className="leading-tight">
          <div className="text-xs text-muted-foreground tracking-[0.12em]">APTER</div>
          <div className="text-[12px] font-semibold tracking-tight">Financial</div>
        </div>
      </Link>

      <div className="flex items-center gap-2">
        <Link href="/performance" className="bt-button hover:bg-muted">
          Performance
        </Link>
        {hasToken ? (
          <Link
            href="/dashboard"
            className="bt-button hover:bg-muted"
          >
            Dashboard
          </Link>
        ) : (
          <>
            <Link href="/login" className="bt-button hover:bg-muted">
              Login
            </Link>
            <Link
              href="/register"
              className="bt-button border-risk-on/40 text-risk-on hover:bg-risk-on/10"
            >
              Get Started
            </Link>
          </>
        )}
      </div>
    </header>
  );
}
