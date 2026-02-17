import {
  LayoutDashboard,
  Briefcase,
  Eye,
  LineChart,
  Search,
  CreditCard,
  Settings,
  HelpCircle,
} from "lucide-react";

export type NavItem = {
  label: string;
  href: string;
  icon: any;
  priority: "HIGH" | "MED" | "LOW";
};

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, priority: "HIGH" },
  { label: "Portfolio", href: "/portfolio", icon: Briefcase, priority: "HIGH" },
  { label: "Watchlist", href: "/watchlist", icon: Eye, priority: "MED" },
  { label: "Market Data", href: "/market-data", icon: LineChart, priority: "MED" },
  { label: "Screener", href: "/screener", icon: Search, priority: "MED" },
  { label: "Plans", href: "/plans", icon: CreditCard, priority: "MED" },
  { label: "Settings", href: "/settings", icon: Settings, priority: "HIGH" },
  { label: "Help & Support", href: "/help-support", icon: HelpCircle, priority: "LOW" },
];
