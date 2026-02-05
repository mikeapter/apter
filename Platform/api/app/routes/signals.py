from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_optional_user
from app.models.user import User
from app.services.plans import PlanTier, plan_definitions, tier_at_least

router = APIRouter(prefix="/v1/signals", tags=["Signals"])


def _repo_root() -> Path:
    # .../Platform/api/app/routes/signals.py -> repo root is parents[5]
    return Path(__file__).resolve().parents[5]


def _signals_dir() -> Path:
    # Platform/runtime/signals
    return _repo_root() / "Platform" / "runtime" / "signals"


def _safe_load_json(p: Path) -> Dict[str, Any] | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _normalize_snapshot(raw: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Normalize various possible signal formats into a consistent payload."""
    signal = raw.get("signal") if isinstance(raw.get("signal"), dict) else {}

    # Primary schema (your runtime snapshots look like this)
    out = {
        "id": raw.get("id"),
        "ts": raw.get("ts"),
        "status": raw.get("status"),
        "execution_mode": raw.get("execution_mode"),
        "symbol": signal.get("symbol"),
        "side": signal.get("side"),
        "qty": signal.get("qty"),
        "strategy_id": signal.get("strategy_id"),
        "confidence": signal.get("confidence"),
        "rationale": signal.get("rationale"),
        "blocked": raw.get("blocked"),
        "reasons": raw.get("reasons"),
        "_source": source,
    }

    # Fallbacks (if you later add other signal shapes)
    if out["ts"] is None and raw.get("timestamp"):
        out["ts"] = raw.get("timestamp")
    if out["symbol"] is None and raw.get("symbol"):
        out["symbol"] = raw.get("symbol")
    if out["side"] is None and raw.get("side"):
        out["side"] = raw.get("side")

    return out


def _load_signal_snapshots() -> List[Dict[str, Any]]:
    """Load snapshots from Platform/runtime/signals.

    Expected files:
      - signal_YYYYMMDD_HHMMSS.json  (your current format)
    """
    base = _signals_dir()
    if not base.exists():
        return []

    files = sorted(base.glob("signal_*.json"))
    snapshots: List[Tuple[int, Dict[str, Any]]] = []

    for p in files:
        raw = _safe_load_json(p)
        if not raw:
            continue

        norm = _normalize_snapshot(raw, source=str(p.name))
        ts = norm.get("ts")
        # If ts missing, use file mtime as fallback
        if not isinstance(ts, int):
            ts = int(p.stat().st_mtime)
            norm["ts"] = ts
        snapshots.append((ts, norm))

    snapshots.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in snapshots]


def _tier_for_request(user: User | None) -> PlanTier:
    if not user:
        return PlanTier.observer
    try:
        return PlanTier(user.subscription_tier)
    except Exception:
        return PlanTier.observer


@router.get("/feed")
def feed(
    limit: int = Query(25, ge=1, le=500),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    """Signals feed with plan gating.

    Observer:
      - 24h delayed
      - limited subset (max 5)
    Signals:
      - realtime
      - higher limit
    Pro:
      - realtime
      - highest limit
    """
    plans = plan_definitions()
    tier = _tier_for_request(user)
    limits = plans[tier]["limits"]

    delay = int(limits["signal_delay_seconds"])
    max_allowed = int(limits["max_signals_per_response"])
    effective_limit = min(limit, max_allowed)

    now_ts = int(datetime.utcnow().timestamp())
    cutoff = now_ts - delay if delay > 0 else None

    snapshots = _load_signal_snapshots()

    if cutoff is not None:
        snapshots = [s for s in snapshots if isinstance(s.get("ts"), int) and s["ts"] <= cutoff]

    # Reduce to subset
    snapshots = snapshots[:effective_limit]

    return {
        "tier": tier.value,
        "mode": "delayed_sample" if delay > 0 else "realtime",
        "signal_delay_seconds": delay,
        "signals": snapshots,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/history")
def history(
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(200, ge=1, le=500),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    """Historical signals. Observer is blocked."""
    plans = plan_definitions()
    tier = _tier_for_request(user)

    if not tier_at_least(tier, PlanTier.signals):
        raise HTTPException(status_code=403, detail="History is not available on Observer tier")

    max_days = int(plans[tier]["limits"]["history_days"])
    effective_days = min(days, max_days)

    max_limit = int(plans[tier]["limits"]["max_signals_per_response"])
    effective_limit = min(limit, max_limit)

    now_ts = int(datetime.utcnow().timestamp())
    cutoff = now_ts - effective_days * 24 * 60 * 60

    snapshots = _load_signal_snapshots()
    snapshots = [s for s in snapshots if isinstance(s.get("ts"), int) and s["ts"] >= cutoff]
    snapshots = snapshots[:effective_limit]

    return {
        "tier": tier.value,
        "days": effective_days,
        "signals": snapshots,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/analytics")
def analytics(
    lookback: int = Query(50, ge=10, le=500),
    user: User | None = Depends(get_optional_user),
) -> Dict[str, Any]:
    """Pro-only analytics (high-level)."""
    tier = _tier_for_request(user)
    if not tier_at_least(tier, PlanTier.pro):
        raise HTTPException(status_code=403, detail="Analytics are only available on Pro tier")

    snapshots = _load_signal_snapshots()[:lookback]

    buys = sum(1 for s in snapshots if str(s.get("side")).upper() == "BUY")
    sells = sum(1 for s in snapshots if str(s.get("side")).upper() == "SELL")
    total = max(1, len(snapshots))

    if buys > sells:
        regime = "RISK_ON"
    elif sells > buys:
        regime = "RISK_OFF"
    else:
        regime = "NEUTRAL"

    confidence = abs(buys - sells) / total

    # Simple volatility proxy from confidence dispersion
    conf_vals = [float(s["confidence"]) for s in snapshots if isinstance(s.get("confidence"), (int, float))]
    if len(conf_vals) >= 2:
        mean = sum(conf_vals) / len(conf_vals)
        var = sum((x - mean) ** 2 for x in conf_vals) / (len(conf_vals) - 1)
        vol_proxy = var ** 0.5
    else:
        vol_proxy = 0.0

    return {
        "tier": tier.value,
        "lookback": lookback,
        "regime": regime,
        "regime_confidence": round(confidence, 4),
        "volatility_proxy": round(vol_proxy, 6),
        "counts": {"buy": buys, "sell": sells, "total": len(snapshots)},
        "generated_at": datetime.utcnow().isoformat(),
    }
