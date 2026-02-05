"use client";

import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import ClientOnly from "../ClientOnly";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <ClientOnly>
      <button
        type="button"
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        className="border rounded px-3 py-1 text-sm flex items-center gap-2"
      >
        {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        <span>Theme</span>
      </button>
    </ClientOnly>
  );
}
