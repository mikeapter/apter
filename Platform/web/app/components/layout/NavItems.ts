import {
  LayoutDashboard,
  Briefcase,
  Bot,
  History,
  Landmark,
  Eye,
  LineChart,
  FileText,
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
  { label: "Bot Configuration", href: "/bot-configuration", icon: Bot, priority: "HIGH" },
  { label: "Trade History", href: "/trade-history", icon: History, priority: "HIGH" },
  { label: "Deposits & Withdrawals", href: "/deposits-withdrawals", icon: Landmark, priority: "HIGH" },
  { label: "Watchlist", href: "/watchlist", icon: Eye, priority: "MED" },
  { label: "Market Data", href: "/market-data", icon: LineChart, priority: "LOW" },
  { label: "Reports & Analytics", href: "/reports-analytics", icon: FileText, priority: "MED" },
  { label: "Plans", href: "/plans", icon: CreditCard, priority: "MED" },
  { label: "Settings", href: "/settings", icon: Settings, priority: "HIGH" },
  { label: "Help & Support", href: "/help-support", icon: HelpCircle, priority: "MED" },
];
