export type BotStatus = "Active" | "Paused" | "Error" | "Unknown";
export type MarketStatus = "Open" | "Closed" | "Pre-market" | "After-hours" | "Unknown";

export type DashboardSummary = {
  total_portfolio_value: number;
  cash_balance: number;
  buying_power: number;

  daily_pnl: number;
  daily_pnl_pct: number;

  total_return_pct: number;

  active_positions: number;
  trades_today: number;
  win_rate_pct: number;

  bot_status: BotStatus;
  market_status: MarketStatus;

  next_market_open?: string;  // ISO or display string
  next_market_close?: string; // ISO or display string
};

export type PerformancePoint = { label: string; value: number };

export type AllocationSlice = { name: string; value: number };

export type ActivityItem = { id: string; text: string; time: string };

export type DashboardPayload = {
  summary: DashboardSummary;
  performance: PerformancePoint[];
  allocation: AllocationSlice[];
  activity: ActivityItem[];
};
