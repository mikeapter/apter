from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
import math

GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}

@dataclass(frozen=True)
class IntegrityPolicy:
    timezone: str = "UTC"
    latency_buffer_ms: int = 500
    min_integrity_grade: str = "B"
    allow_reconstructed_in_backtests: bool = False
    require_known_ts: bool = True
    require_survivorship_free_universe: bool = True
    allow_latest_adjusted_history: bool = False

def _is_finite(x: Any) -> bool:
    try:
        return x is not None and math.isfinite(float(x))
    except Exception:
        return False

def enforce_point_in_time(rows: Iterable[Dict[str, Any]], decision_ts_utc: int, policy: IntegrityPolicy) -> List[Dict[str, Any]]:
    """
    Filters rows so nothing 'knowable' after decision time leaks in.
    Assumes timestamps are epoch milliseconds UTC.
    """
    out = []
    for r in rows:
        known_ts = r.get("known_ts", r.get("received_ts"))
        if policy.require_known_ts and known_ts is None:
            continue
        if known_ts is not None and int(known_ts) > int(decision_ts_utc):
            continue
        out.append(r)
    return out

def enforce_latency_buffer(rows: Iterable[Dict[str, Any]], decision_ts_utc: int, policy: IntegrityPolicy) -> List[Dict[str, Any]]:
    cutoff = int(decision_ts_utc) - int(policy.latency_buffer_ms)
    return [r for r in rows if int(r.get("data_ts", r.get("ts", 0))) <= cutoff]

def validate_quote_row(r: Dict[str, Any]) -> bool:
    bid, ask = r.get("bid"), r.get("ask")
    if not (_is_finite(bid) and _is_finite(ask)):
        return False
    if ask < bid:
        return False
    if not (_is_finite(r.get("bid_size", 0)) and _is_finite(r.get("ask_size", 0))):
        return False
    if float(r.get("bid_size", 0)) < 0 or float(r.get("ask_size", 0)) < 0:
        return False
    return True

def validate_bar_row(r: Dict[str, Any]) -> bool:
    o,h,l,c,v = r.get("o"), r.get("h"), r.get("l"), r.get("c"), r.get("v")
    if not all(_is_finite(x) for x in [o,h,l,c]):
        return False
    if not _is_finite(v):
        return False
    if float(v) < 0:
        return False
    if float(h) < float(l):
        return False
    if not (float(l) <= float(o) <= float(h)): return False
    if not (float(l) <= float(c) <= float(h)): return False
    return True

def grade_ok(r: Dict[str, Any], policy: IntegrityPolicy) -> bool:
    grade = (r.get("integrity_grade") or "A").upper()
    return GRADE_ORDER.get(grade, 99) <= GRADE_ORDER.get(policy.min_integrity_grade.upper(), 1)

def reject_reconstructed_for_backtest(r: Dict[str, Any], policy: IntegrityPolicy) -> bool:
    if policy.allow_reconstructed_in_backtests:
        return True
    return not bool(r.get("is_reconstructed", False))

def clean_rows(feed: str, rows: Iterable[Dict[str, Any]], policy: IntegrityPolicy, *, mode: str) -> List[Dict[str, Any]]:
    """
    mode: 'live' or 'backtest' (affects reconstructed-data gating)
    """
    out = []
    for r in rows:
        if not grade_ok(r, policy):
            continue
        if mode == "backtest" and not reject_reconstructed_for_backtest(r, policy):
            continue

        if feed == "quote" and not validate_quote_row(r):
            continue
        if feed == "bar" and not validate_bar_row(r):
            continue

        out.append(r)
    return out
