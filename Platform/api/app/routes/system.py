from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api", tags=["system"])

@router.get("/health")
def health():
    return {"ok": True, "service": "bottrader-api", "time": datetime.now().isoformat(timespec="seconds")}

def _dashboard_payload(period: str):
    # Slight variations so you can SEE the toggles work immediately
    base = {
        "today": 1.0,
        "week": 1.8,
        "month": 3.2,
        "year": 8.7,
        "all": 12.4,
    }.get(period, 1.0)

    total_value = round(152340.22 * (1 + (base * 0.002)), 2)
    cash = round(18450.11 * (1 - (base * 0.001)), 2)
    buying = round(32810.77 * (1 - (base * 0.0005)), 2)

    # Force a negative example for "week" so you can confirm RED renders:
    daily_pnl = -420.55 if period == "week" else 1240.55
    daily_pnl_pct = round((daily_pnl / 152340.22) * 100, 2)

    performance = [
        {"label": "M", "value": 100},
        {"label": "T", "value": int(105 + base)},
        {"label": "W", "value": int(103 + base)},
        {"label": "T", "value": int(112 + base)},
        {"label": "F", "value": int(118 + base)},
        {"label": "S", "value": int(116 + base)},
        {"label": "S", "value": int(121 + base)},
    ]

    allocation = [
        {"name": "Equities", "value": 62},
        {"name": "Cash", "value": 18},
        {"name": "ETFs", "value": 12},
        {"name": "Crypto", "value": 8},
    ]

    top_movers = [
        {"symbol": "AAPL", "change_pct": 2.14},
        {"symbol": "MSFT", "change_pct": -1.08},
        {"symbol": "NVDA", "change_pct": 3.77},
        {"symbol": "TSLA", "change_pct": -2.31},
    ]

    return {
        "period": period,
        "summary": {
            "total_portfolio_value": total_value,
            "cash_balance": cash,
            "buying_power": buying,
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": daily_pnl_pct,
            "total_return_pct": 18.40,
            "active_positions": 7,
            "trades_today": 3,
            "win_rate_pct": 56.3,
            "bot_status": "Paused",
            "market_status": "Closed",
            "next_market_open": "9:30 AM ET (Mon-Fri)",
            "next_market_close": None,
        },
        "performance": performance,
        "allocation": allocation,
        "top_movers": top_movers,
        "activity": [
            {"id": "a1", "text": "Dashboard endpoint online", "time": "now"},
            {"id": "a2", "text": f"Period set: {period}", "time": "now"},
            {"id": "a3", "text": f"Server time: {datetime.now().strftime('%I:%M %p')}", "time": "now"},
        ],
    }

@router.get("/dashboard")
def dashboard(period: str = Query(default="today", pattern="^(today|week|month|year|all)$")):
    return _dashboard_payload(period)
