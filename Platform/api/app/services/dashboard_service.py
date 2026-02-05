from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from app.services.bot_runtime import get_status


def build_dashboard_payload() -> Dict[str, Any]:
    # Bot status from runtime (real)
    st = get_status("opening")
    bot_status = "Active" if st.get("running") else "Paused"

    # Market status placeholder (we’ll make real later)
    market_status = "Closed"
    next_market_open = "9:30 AM ET (Mon–Fri)"

    summary = {
        "total_portfolio_value": 152340.22,
        "cash_balance": 18450.11,
        "buying_power": 32810.77,
        "daily_pnl": 1240.55,
        "daily_pnl_pct": 0.82,
        "total_return_pct": 18.40,
        "active_positions": 7,
        "trades_today": 3,
        "win_rate_pct": 56.3,
        "bot_status": bot_status,
        "market_status": market_status,
        "next_market_open": next_market_open,
        "next_market_close": None,
    }

    performance = [
        {"label": "M", "value": 100},
        {"label": "T", "value": 105},
        {"label": "W", "value": 103},
        {"label": "T", "value": 112},
        {"label": "F", "value": 118},
        {"label": "S", "value": 116},
        {"label": "S", "value": 121},
    ]

    allocation = [
        {"name": "Equities", "value": 62},
        {"name": "Cash", "value": 18},
        {"name": "ETFs", "value": 12},
        {"name": "Crypto", "value": 8},
    ]

    activity = [
        {"id": "a1", "text": "Dashboard endpoint online", "time": "now"},
        {"id": "a2", "text": f"Opening bot: {bot_status}", "time": "now"},
        {"id": "a3", "text": f"Server time: {datetime.now().strftime('%I:%M %p')}", "time": "now"},
    ]

    return {
        "summary": summary,
        "performance": performance,
        "allocation": allocation,
        "activity": activity,
    }
