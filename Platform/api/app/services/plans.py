from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List


class PlanTier(str, Enum):
    """Subscription tiers for Apter (signals-only trading tool)."""

    observer = "observer"
    signals = "signals"
    pro = "pro"


# Emails granted complimentary Pro access (case-insensitive).
COMPLIMENTARY_PRO_EMAILS: set[str] = {
    "siegetheday03@gmail.com",
    "mapter16@gmail.com",
}


def is_complimentary_pro(email: str) -> bool:
    """Return True if *email* has complimentary Pro access."""
    return email.lower() in COMPLIMENTARY_PRO_EMAILS


_TIER_RANK = {
    PlanTier.observer: 0,
    PlanTier.signals: 1,
    PlanTier.pro: 2,
}


def tier_at_least(current: PlanTier, required: PlanTier) -> bool:
    return _TIER_RANK[current] >= _TIER_RANK[required]


def plan_definitions() -> Dict[PlanTier, Dict[str, Any]]:
    """Canonical plan definitions. Keep wording aligned with your business plan."""
    return {
        PlanTier.observer: {
            "tier": PlanTier.observer.value,
            "name": "Observer Tier",
            "price_usd_month": 0,
            "target_user": (
                "Prospective users seeking to evaluate methodology and build trust before commitment."
            ),
            "features": [
                "Daily or weekly market outlook (high-level)",
                "High-level market regime indicator (Risk-On / Neutral / Risk-Off)",
                "Limited sample signal subset",
                "Delayed signal visibility (24-hour lag)",
                "Plain-language explanations of model interpretation",
                "Educational content on risk management and discipline",
            ],
            "exclusions": [
                "Real-time signal access",
                "Complete buy/sell recommendations",
                "Alert notifications",
                "Historical signal archive",
                "Any automated execution capabilities",
            ],
            "limits": {
                "signal_delay_seconds": 24 * 60 * 60,
                "max_signals_per_response": 5,
                "history_days": 0,
                "alerts": False,
            },
        },
        PlanTier.signals: {
            "tier": PlanTier.signals.value,
            "name": "Signals Tier",
            "price_usd_month": 25,
            "target_user": "Self-directed traders who want clear, consistent, rules-based signals.",
            "features": [
                "Everything in Observer",
                "Real-time buy/sell signal feed",
                "Comprehensive daily signal coverage",
                "Precise signal timestamps",
                "Clear identification of non-trading days (via feed metadata)",
                "Market regime with confidence context",
                "Signal change alerts (email/push) [scaffold only in Step 1]",
                "Read-only access to recent signal history",
                "Consistent rules-based analytical framework",
            ],
            "exclusions": [
                "Automated trade execution",
                "Personalized portfolio recommendations",
                "Position sizing guidance",
                "Account-specific investment advice",
            ],
            "limits": {
                "signal_delay_seconds": 0,
                "max_signals_per_response": 100,
                "history_days": 7,
                "alerts": True,  # scaffold only in Step 1
            },
        },
        PlanTier.pro: {
            "tier": PlanTier.pro.value,
            "name": "Pro Tier",
            "price_usd_month": 49,
            "target_user": "Advanced users who want deeper analytics and extended history.",
            "features": [
                "Everything in Signals",
                "Extended historical signal archive",
                "Signal strength + confidence bands (where available)",
                "Volatility + regime analytics (high-level)",
                "Model rationale (non-technical explanation)",
                "Strategic commentary during drawdowns (via outlook endpoints)",
                "Priority early access to new features",
                "Priority platform updates and support",
                "Eligibility for future auto-trading (pending licensing) [NOT implemented]",
            ],
            "exclusions": [
                "Personalized portfolio advice",
                "Guaranteed investment outcomes",
                "Manual trade execution by platform (until licensed)",
            ],
            "limits": {
                "signal_delay_seconds": 0,
                "max_signals_per_response": 500,
                "history_days": 365,
                "alerts": True,  # scaffold only in Step 1
            },
        },
    }


def public_plans_payload() -> Dict[str, Any]:
    plans = plan_definitions()
    ordered = [plans[PlanTier.observer], plans[PlanTier.signals], plans[PlanTier.pro]]
    return {
        "plans": ordered,
        "as_of": "v1",
    }
