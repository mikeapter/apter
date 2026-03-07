import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./pages/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",

        panel: "hsl(var(--panel))",
        "panel-2": "hsl(var(--panel-2))",

        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",

        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",

        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",

        "risk-on": "hsl(var(--risk-on))",
        "risk-neutral": "hsl(var(--risk-neutral))",
        "risk-off": "hsl(var(--risk-off))",
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "Liberation Mono",
          "Courier New",
          "monospace",
        ],
      },
      borderRadius: {
        "3xl": "1.5rem", // 24px — sheets, modals
        "2xl": "1rem",   // 16px — mobile cards
        xl: "0.75rem",   // 12px — buttons, inputs
        lg: "0.375rem",  // 6px
        md: "0.25rem",   // 4px
        sm: "0.1875rem", // 3px
      },
    },
  },
  plugins: [],
};

export default config;
