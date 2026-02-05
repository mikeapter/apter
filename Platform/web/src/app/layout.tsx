import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "BotTrader — Control Plane",
  description: "Signals-only trading tool. No auto-execution.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      {/* Hard-force background using CSS var so no class can override it */}
      <body style={{ backgroundColor: "var(--bg)", color: "var(--fg)" }}>
        {children}
      </body>
    </html>
  );
}
