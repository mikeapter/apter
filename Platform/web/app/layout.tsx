import type { Metadata, Viewport } from "next";
import "./globals.css";
import Providers from "./providers";
import { Analytics } from "./components/Analytics";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
  themeColor: "#000023",
};

export const metadata: Metadata = {
  title: "Apter Financial — Disciplined Trading Intelligence",
  description:
    "Rules-based signals with regime context and transparent rationale. Signals-only trading intelligence built for control.",
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Apter Financial",
  },
  openGraph: {
    title: "Apter Financial — Disciplined Trading Intelligence",
    description:
      "Rules-based signals with regime context and transparent rationale.",
    siteName: "Apter Financial",
    type: "website",
  },
  other: {
    "mobile-web-app-capable": "yes",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="apple-touch-icon" sizes="180x180" href="/icons/apple-touch-icon.png" />
      </head>
      <body className="min-h-screen font-sans text-[14px] leading-[1.5] tracking-[0.01em] bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
        <Analytics />
      </body>
    </html>
  );
}
