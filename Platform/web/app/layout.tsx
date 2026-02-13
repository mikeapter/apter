import "./globals.css";
import Providers from "./providers";

export const metadata = {
  title: "Apter Financial",
  description: "Disciplined trading signals. Rules-based market analysis platform.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen font-sans text-[13.5px] leading-[1.25] tracking-[0.01em] bg-background text-foreground">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
