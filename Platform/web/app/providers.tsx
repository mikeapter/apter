"use client";

import { ThemeProvider } from "next-themes";

/**
 * Institutional UI standard:
 * - Fixed dark palette (Bloomberg-inspired)
 * - No system theme switching
 */
export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      forcedTheme="dark"
      enableSystem={false}
      disableTransitionOnChange
    >
      {children}
    </ThemeProvider>
  );
}
