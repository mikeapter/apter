from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_optional_user
from app.models.user import User
from app.routes.signals import _load_signal_snapshots
from app.services.plans import PlanTier

router = APIRouter(prefix="/v1/insights", tags=["Insights"])


def _regime_from_recent(n: int = 50) -> Dict[str, Any]:
    snaps = _load_signal_snapshots()[:n]
    buys = sum(1 for s in snaps if str(s.get("side")).upper() == "BUY")
    sells = sum(1 for s in snaps if str(s.get("side")).upper() == "SELL")
    total = max(1, len(snaps))

    if buys > sells:
        regime = "RISK_ON"
    elif sells > buys:
        regime = "RISK_OFF"
    else:
        regime = "NEUTRAL"

    confidence = abs(buys - sells) / total

    return {
        "regime": regime,
        "confidence": round(confidence, 4),
        "counts": {"buy": buys, "sell": sells, "total": len(snaps)},
    }


@router.get("/regime")
def regime(
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    tier = PlanTier(user.subscription_tier) if user else PlanTier.observer
    r = _regime_from_recent(50)

    # Observer gets high-level only (no deep analytics)
    return {
        "tier": tier.value,
        "regime": r["regime"],
        "confidence": r["confidence"],
        "as_of": datetime.utcnow().isoformat(),
    }


@router.get("/outlook")
def outlook(
    cadence: str = Query("daily", pattern="^(daily|weekly)$"),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    tier = PlanTier(user.subscription_tier) if user else PlanTier.observer
    r = _regime_from_recent(100 if cadence == "weekly" else 50)

    # Plain-language outlook. Keep it non-advice, educational framing.
    text = (
        f"{cadence.title()} outlook: Current regime is {r['regime']} "
        f"(confidence {r['confidence']}). Focus on discipline: define risk first, "
        "size conservatively, and avoid impulsive trades. This is a signals tool—"
        "not personalized investment advice."
    )

    # Paid tiers can receive a bit more context (still non-advice)
    extra = None
    if tier != PlanTier.observer:
        extra = (
            "If volatility expands, reduce exposure and require stronger confirmation. "
            "If regime flips persistently, expect signal churn and prioritize risk limits."
        )

    return {
        "tier": tier.value,
        "cadence": cadence,
        "regime": r["regime"],
        "confidence": r["confidence"],
        "outlook": text,
        "extra_context": extra,
        "as_of": datetime.utcnow().isoformat(),
    }
