"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  // Prevent hydration mismatch: don’t render theme-dependent icon until mounted
  if (!mounted) {
    return (
      <button className="px-3 py-2 rounded-md border border-white/15 text-sm">
        Theme
      </button>
    );
  }

  const isDark = theme === "dark";

  return (
    <button
      className="flex items-center gap-2 px-3 py-2 rounded-md border border-white/15 hover:bg-white/10 text-sm"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label="Toggle theme"
    >
      {isDark ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
      <span>{isDark ? "Dark" : "Light"}</span>
    </button>
  );
}
