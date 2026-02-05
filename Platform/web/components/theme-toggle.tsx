"use client";

import * as React from "react";
import { useTheme } from "next-themes";

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  const current = theme ?? resolvedTheme ?? "dark";
  const next = current === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs hover:bg-white/10"
      onClick={() => setTheme(next)}
      aria-label="Toggle theme"
      title="Toggle theme"
    >
      <span>{current === "dark" ? "🌙" : "☀️"}</span>
      <span>{current === "dark" ? "Dark" : "Light"}</span>
    </button>
  );
}
