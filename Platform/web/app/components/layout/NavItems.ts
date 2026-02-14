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
  LogOut,
} from "lucide-react";
import type { PlanTier } from "@/lib/tiers";

export type NavItem = {
  label: string;
  href: string;
  icon: any;
  priority: "HIGH" | "MED" | "LOW";
  minTier?: PlanTier;
};

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard, priority: "HIGH" },
  { label: "Portfolio", href: "/portfolio", icon: Briefcase, priority: "HIGH", minTier: "signals" },
  { label: "Bot Configuration", href: "/bot-configuration", icon: Bot, priority: "HIGH", minTier: "pro" },
  { label: "Trade History", href: "/trade-history", icon: History, priority: "HIGH", minTier: "signals" },
  { label: "Deposits & Withdrawals", href: "/deposits-withdrawals", icon: Landmark, priority: "HIGH", minTier: "signals" },
  { label: "Watchlist", href: "/watchlist", icon: Eye, priority: "MED" },
  { label: "Market Data", href: "/market-data", icon: LineChart, priority: "LOW" },
  { label: "Reports & Analytics", href: "/reports-analytics", icon: FileText, priority: "MED", minTier: "pro" },
  { label: "Plans", href: "/plans", icon: CreditCard, priority: "MED" },
  { label: "Settings", href: "/settings", icon: Settings, priority: "HIGH" },
  { label: "Help & Support", href: "/help-support", icon: HelpCircle, priority: "MED" },
  { label: "Logout", href: "/logout", icon: LogOut, priority: "LOW" },
];
