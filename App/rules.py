from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Dict, List, Optional
import yaml

@dataclass
class ComplianceResult:
    ok: bool
    reasons: List[str]

def load_rules(path: str = "ips_rules.yaml") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _norm(s: Any) -> str:
    """Normalize strings so 'stop-market' == 'stop_market' == 'Stop Market'."""
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = s.replace(" ", "_").replace("-", "_")
    return s

def _parse_hhmm(s: str) -> time:
    hh, mm = s.split(":")
    return time(int(hh), int(mm))

def is_in_blocked_window(now: datetime, blocked_windows: List[Dict[str, str]]) -> bool:
    t = now.time()
    for w in blocked_windows:
        start = _parse_hhmm(w["start"])
        end = _parse_hhmm(w["end"])
        if start <= t <= end:
            return True
    return False

def _get_exec_bool(exec_rules: Dict[str, Any], *keys: str, default: bool = True) -> bool:
    """
    Read a boolean from multiple possible YAML keys.
    default=True because IPS restrictions should be ON unless explicitly turned off.
    """
    for k in keys:
        if k in exec_rules:
            return bool(exec_rules[k])
    return default

def check_order(order: Dict[str, Any], rules: Dict[str, Any], now: Optional[datetime] = None) -> ComplianceResult:
    now = now or datetime.now()
    reasons: List[str] = []

    # --- Universe checks
    universe = rules.get("universe", {})
    eligible = {_norm(x) for x in universe.get("eligible_asset_classes", [])}
    asset_class = _norm(order.get("asset_class"))

    if eligible and asset_class not in eligible:
        reasons.append(f"Asset class not eligible: {order.get('asset_class')}")

    # Crypto gate
    crypto_cfg = rules.get("crypto", {})
    instrument_type = _norm(order.get("instrument_type"))
    if instrument_type.startswith("crypto") or asset_class.startswith("crypto"):
        if not bool(crypto_cfg.get("allowed", False)):
            reasons.append("Crypto is disabled by IPS config (crypto.allowed=false)")

    # --- Prohibited instruments / behaviors
    prohibited = rules.get("prohibited", {})
    prohibited_instruments = {_norm(x) for x in prohibited.get("instruments", [])}
    prohibited_behaviors = {_norm(x) for x in prohibited.get("behaviors", [])}

    if prohibited_instruments and instrument_type in prohibited_instruments:
        reasons.append(f"Prohibited instrument: {order.get('instrument_type')}")

    for flag in order.get("behavior_flags", []) or []:
        if _norm(flag) in prohibited_behaviors:
            reasons.append(f"Prohibited behavior: {flag}")

    # --- Execution rules
    exec_rules = rules.get("execution", {})

    # Order type allow/deny lists (normalized)
    allowed_order_types = {_norm(x) for x in exec_rules.get("allowed_order_types", [])}
    disallowed_order_types = {_norm(x) for x in exec_rules.get("disallowed_order_types", [])}

    ot = _norm(order.get("order_type"))

    # IPS HARD DEFAULT: stop_market is not allowed (even if YAML list is missing)
    if not disallowed_order_types:
        disallowed_order_types = {"stop_market"}
    else:
        disallowed_order_types.add("stop_market")

    if ot in disallowed_order_types:
        reasons.append(f"Order type disallowed: {order.get('order_type')}")

    # If YAML provided an allowed list, enforce it
    if allowed_order_types and ot not in allowed_order_types:
        reasons.append(f"Order type not in allowed list: {order.get('order_type')}")

    # Time windows (support two possible key names)
    blocked = exec_rules.get("blocked_time_windows") or exec_rules.get("avoid_times") or []
    if blocked and is_in_blocked_window(now, blocked):
        reasons.append("Trade attempted during blocked time window")

    # Liquidity / spread restrictions (IPS defaults ON)
    liq = order.get("liquidity", {}) or {}
    is_thin = bool(liq.get("is_thin", False))
    is_wide = bool(liq.get("is_wide_spread", False))

    block_market_when_thin = _get_exec_bool(
        exec_rules,
        "no_market_orders_in_thin_assets",
        "block_market_orders_when_thin",
        default=True
    )

    block_when_wide_spread = _get_exec_bool(
        exec_rules,
        "no_aggressive_crossing_in_wide_spreads",
        "block_when_wide_spread",
        default=True
    )

    if block_market_when_thin and ot == "market" and is_thin:
        reasons.append("Market order blocked: thin liquidity")

    if block_when_wide_spread and is_wide:
        reasons.append("Blocked: wide spread / no aggressive crossing")

    return ComplianceResult(ok=(len(reasons) == 0), reasons=reasons)
