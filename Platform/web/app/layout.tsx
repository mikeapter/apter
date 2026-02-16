import "./globals.css";
import Providers from "./providers";
import { Analytics } from "./components/Analytics";

export const metadata = {
  title: "Apter Financial — Disciplined Trading Intelligence",
  description:
    "Rules-based signals with regime context and transparent rationale. Signals-only trading intelligence built for control.",
  openGraph: {
    title: "Apter Financial — Disciplined Trading Intelligence",
    description:
      "Rules-based signals with regime context and transparent rationale.",
    siteName: "Apter Financial",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen font-sans text-[14px] leading-[1.5] tracking-[0.01em] bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
        <Analytics />
      </body>
    </html>
  );
}
