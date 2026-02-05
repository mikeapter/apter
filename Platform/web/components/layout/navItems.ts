import {
  Banknote,
  Briefcase,
  ChartLine,
  CircleHelp,
  Eye,
  FileText,
  History,
  LayoutDashboard,
  Settings,
  SlidersHorizontal
} from "lucide-react";

export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/bot-configuration", label: "Bot Configuration", icon: SlidersHorizontal },
  { href: "/trade-history", label: "Trade History", icon: History },
  { href: "/transfers", label: "Deposits & Withdrawals", icon: Banknote },
  { href: "/watchlist", label: "Watchlist", icon: Eye },
  { href: "/market-data", label: "Market Data", icon: ChartLine },
  { href: "/reports", label: "Reports & Analytics", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/support", label: "Help & Support", icon: CircleHelp }
] as const;

export type NavItem = (typeof NAV_ITEMS)[number];
