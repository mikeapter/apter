import {
  LayoutDashboard,
  Briefcase,
  Eye,
  LineChart,
  Search,
  CreditCard,
  HelpCircle,
  Sparkles,
  BarChart3,
} from "lucide-react";

export type NavItem = {
  label: string;
  href: string;
  icon: any;
  priority: "HIGH" | "MED" | "LOW";
};

// Settings removed from sidebar — accessible only via user avatar dropdown
export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, priority: "HIGH" },
  { label: "Daily Brief", href: "/dashboard/ai-overview", icon: Sparkles, priority: "HIGH" },
  { label: "Portfolio", href: "/portfolio", icon: Briefcase, priority: "HIGH" },
  { label: "Watchlist", href: "/watchlist", icon: Eye, priority: "MED" },
  { label: "Market Data", href: "/market-data", icon: LineChart, priority: "MED" },
  { label: "Screener", href: "/screener", icon: Search, priority: "MED" },
  { label: "Performance", href: "/performance", icon: BarChart3, priority: "MED" },
  { label: "Plans", href: "/plans", icon: CreditCard, priority: "MED" },
  { label: "Help & Support", href: "/help-support", icon: HelpCircle, priority: "LOW" },
];
