from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _upper(x: Any, default: str = "") -> str:
    if x is None:
        return default
    return str(x).upper().strip()


def _mid(bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    if bid is None or ask is None:
        return None
    return (float(bid) + float(ask)) / 2.0


def _spread_bps(bid: Optional[float], ask: Optional[float], ref: Optional[float]) -> Optional[float]:
    if bid is None or ask is None:
        return None
    if ref is None or ref <= 0:
        ref = _mid(bid, ask)
    if ref is None or ref <= 0:
        return None
    spread = float(ask) - float(bid)
    return (spread / ref) * 10000.0


def _side_sign(side: str) -> int:
    s = _upper(side)
    if s in ("BUY", "B", "LONG"):
        return +1
    if s in ("SELL", "S", "SHORT"):
        return -1
    return +1


@dataclass
class ExecutionChildOrder:
    """
    A child order spec for algos (TWAP/VWAP/ICEBERG/POV).
    This is *planning* only; your broker adapter decides how to implement.
    """
    qty: int
    order_type: str  # "LIMIT" / "MARKETABLE_LIMIT" / "ICEBERG" / etc.
    limit_price: Optional[float] = None
    tif: str = "DAY"
    start_ts: Optional[float] = None
    end_ts: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionPlan:
    method: str  # DIRECT / TWAP / VWAP / ICEBERG / POV
    order_type: str  # LIMIT / MARKETABLE_LIMIT / MARKET
    qty: int
    limit_price: Optional[float]
    children: List[ExecutionChildOrder]
    est_slippage_bps: float
    hard_max_slippage_bps: float
    reason: str
    meta: Dict[str, Any]


class ExecutionAlpha:
    """
    STEP 15: execution alpha module
    - chooses execution method (DIRECT vs TWAP/VWAP/ICEBERG/POV)
    - aims to minimize slippage by:
        * preferring marketable limits over pure market orders
        * avoiding crossing wide spreads
        * slicing large orders (size vs liquidity) into TWAP/POV/etc.
    - outputs a plan; your OrderExecutor/broker adapter executes it.

    Inputs expected in `quote`:
      quote = { "bid": float|None, "ask": float|None, "last": float|None, "mid": float|None }

    Inputs expected in `meta` (optional):
      meta = {
        "expected_price": float,        # price at signal generation (Strategy notion)
        "volatility": float,            # intraday vol proxy (0.0-1.0 scale ok)
        "avg_minute_volume": float,     # liquidity proxy
        "use_vwap": bool,               # force VWAP method
        "urgent": bool,                 # signal urgency
      }
    """

    def __init__(self, config_path: Union[str, Path]):
        self.config_path = Path(config_path)
        self.cfg = self._load_config(self.config_path)

    def _load_config(self, p: Path) -> Dict[str, Any]:
        if not p.exists():
            raise FileNotFoundError(f"ExecutionAlpha config missing: {p}")
        with open(p, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # ---------- public API ----------

    def build_plan(
        self,
        symbol: str,
        side: str,
        qty: int,
        quote: Dict[str, Any],
        meta: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        meta = meta or {}
        side_u = _upper(side, "BUY")
        qty_i = max(0, _safe_int(qty, 0))

        bid = quote.get("bid", None)
        ask = quote.get("ask", None)
        last = quote.get("last", None)
        mid = quote.get("mid", None)
        if mid is None:
            mid = _mid(_safe_float(bid, None) if bid is not None else None,
                       _safe_float(ask, None) if ask is not None else None)

        bid_f = None if bid is None else _safe_float(bid, None)
        ask_f = None if ask is None else _safe_float(ask, None)
        last_f = None if last is None else _safe_float(last, None)
        mid_f = None if mid is None else _safe_float(mid, None)

        # Strategy concept: expected price = price at signal generation.
        expected_price = meta.get("expected_price", None)
        if expected_price is None:
            expected_price = mid_f or last_f or (ask_f if side_u == "BUY" else bid_f)
        expected_price_f = None if expected_price is None else _safe_float(expected_price, None)

        # Config knobs
        hard_max_slippage_bps = _safe_float(self.cfg.get("max_acceptable_slippage_bps", 5.0), 5.0)
        wide_spread_bps = _safe_float(self.cfg.get("wide_spread_bps", 6.0), 6.0)
        marketable_limit_offset_bps = _safe_float(self.cfg.get("marketable_limit_offset_bps", 1.0), 1.0)
        large_order_participation_threshold = _safe_float(self.cfg.get("large_order_participation_threshold", 0.10), 0.10)
        twap_slices = _safe_int(self.cfg.get("twap_slices", 10), 10)
        twap_minutes = _safe_float(self.cfg.get("twap_minutes", 5.0), 5.0)
        pov_participation_rate = _safe_float(self.cfg.get("pov_participation_rate", 0.15), 0.15)
        iceberg_display_pct = _safe_float(self.cfg.get("iceberg_display_pct", 0.15), 0.15)
        volatility_threshold = _safe_float(self.cfg.get("volatility_threshold", 0.012), 0.012)

        # Liquidity proxies
        avg_minute_vol = _safe_float(meta.get("avg_minute_volume", self.cfg.get("default_avg_minute_volume", 10000)), 10000.0)
        volatility = _safe_float(meta.get("volatility", 0.0), 0.0)
        urgent = bool(meta.get("urgent", False))
        force_vwap = bool(meta.get("use_vwap", False))
        force_iceberg = bool(meta.get("use_iceberg", False))

        # Spread
        sbps = _spread_bps(bid_f, ask_f, expected_price_f or mid_f or last_f)
        is_wide_spread = (sbps is not None and sbps >= wide_spread_bps)

        # Large order logic: Strategy rule
        # If order_size > avg_volume_per_minute * 0.10 => algorithmic execution
        large_threshold_qty = max(1.0, avg_minute_vol * large_order_participation_threshold)
        is_large = float(qty_i) > large_threshold_qty

        reason_parts: List[str] = []
        reason_parts.append(f"spread_bps={sbps:.2f}" if sbps is not None else "spread_bps=NA")
        reason_parts.append(f"wide_spread={is_wide_spread}")
        reason_parts.append(f"avg_minute_vol={avg_minute_vol:.0f}")
        reason_parts.append(f"large_threshold_qty={large_threshold_qty:.0f}")
        reason_parts.append(f"is_large={is_large}")
        reason_parts.append(f"volatility={volatility:.5f}")
        reason_parts.append(f"urgent={urgent}")
        reason_parts.append(f"force_vwap={force_vwap}")
        reason_parts.append(f"force_iceberg={force_iceberg}")

        # Decide method
        method = "DIRECT"

        if force_vwap:
            method = "VWAP"
        elif force_iceberg:
            method = "ICEBERG"
        elif is_large:
            # Strategy: if volatility low => TWAP else POV
            method = "TWAP" if volatility < volatility_threshold else "POV"
        else:
            method = "DIRECT"

        # Decide order type and limit price strategy
        # Strategy: prefer marketable limit, avoid crossing wide spreads
        order_type = "MARKETABLE_LIMIT"
        limit_price = None

        # Set a marketable limit price offset (bps), but reduce aggressiveness if spread is wide.
        ref_px = expected_price_f or mid_f or last_f
        if ref_px is None or ref_px <= 0:
            ref_px = 0.0

        offset_bps = marketable_limit_offset_bps

        if is_wide_spread:
            # If wide spread, do not cross; use passive/near-mid limit
            order_type = "LIMIT"
            if mid_f is not None and mid_f > 0:
                # Place at mid (or slightly inside)
                limit_price = mid_f
            else:
                # Fallback: use bid/ask depending on side
                limit_price = bid_f if side_u == "BUY" else ask_f
            reason_parts.append("wide_spread=>LIMIT(passive)")
        else:
            # Normal conditions: marketable limit near touch
            if side_u == "BUY":
                # pay up slightly to increase fill probability
                base = ask_f if ask_f is not None else (mid_f or last_f or ref_px)
                limit_price = base * (1.0 + offset_bps / 10000.0)
            else:
                base = bid_f if bid_f is not None else (mid_f or last_f or ref_px)
                limit_price = base * (1.0 - offset_bps / 10000.0)
            reason_parts.append("normal_spread=>MARKETABLE_LIMIT")

        # Urgency override: if urgent and not wide spread, allow more aggressive marketable limit
        if urgent and not is_wide_spread:
            offset_bps = _safe_float(self.cfg.get("urgent_marketable_limit_offset_bps", 2.0), 2.0)
            if side_u == "BUY":
                base = ask_f if ask_f is not None else (mid_f or last_f or ref_px)
                limit_price = base * (1.0 + offset_bps / 10000.0)
            else:
                base = bid_f if bid_f is not None else (mid_f or last_f or ref_px)
                limit_price = base * (1.0 - offset_bps / 10000.0)
            reason_parts.append("urgent=>wider_marketable_offset")

        # Build children for algo methods
        children: List[ExecutionChildOrder] = []
        now = time.time()

        if method == "DIRECT":
            # no children
            pass

        elif method == "TWAP":
            # Slicing qty into N slices over twap_minutes
            n = max(1, twap_slices)
            duration_sec = max(30.0, twap_minutes * 60.0)
            slice_qty_base = qty_i // n
            remainder = qty_i - slice_qty_base * n
            for i in range(n):
                q_i = slice_qty_base + (1 if i < remainder else 0)
                if q_i <= 0:
                    continue
                start_i = now + (duration_sec * i / n)
                end_i = now + (duration_sec * (i + 1) / n)
                children.append(
                    ExecutionChildOrder(
                        qty=q_i,
                        order_type=order_type,
                        limit_price=limit_price,
                        tif="DAY",
                        start_ts=start_i,
                        end_ts=end_i,
                        meta={"slice": i + 1, "slices": n, "algo": "TWAP"},
                    )
                )

        elif method == "VWAP":
            # VWAP: we model as slices (broker can implement real VWAP)
            n = max(1, _safe_int(self.cfg.get("vwap_slices", 12), 12))
            duration_sec = max(60.0, _safe_float(self.cfg.get("vwap_minutes", 10.0), 10.0) * 60.0)
            slice_qty_base = qty_i // n
            remainder = qty_i - slice_qty_base * n
            for i in range(n):
                q_i = slice_qty_base + (1 if i < remainder else 0)
                if q_i <= 0:
                    continue
                start_i = now + (duration_sec * i / n)
                end_i = now + (duration_sec * (i + 1) / n)
                children.append(
                    ExecutionChildOrder(
                        qty=q_i,
                        order_type=order_type,
                        limit_price=limit_price,
                        tif="DAY",
                        start_ts=start_i,
                        end_ts=end_i,
                        meta={"slice": i + 1, "slices": n, "algo": "VWAP"},
                    )
                )

        elif method == "ICEBERG":
            # ICEBERG: create sequential child orders with display quantity
            display_qty = max(1, int(math.ceil(qty_i * iceberg_display_pct)))
            n = max(1, int(math.ceil(qty_i / display_qty)))
            remaining = qty_i
            for i in range(n):
                q_i = min(display_qty, remaining)
                remaining -= q_i
                children.append(
                    ExecutionChildOrder(
                        qty=q_i,
                        order_type="ICEBERG",
                        limit_price=limit_price,
                        tif="DAY",
                        start_ts=None,
                        end_ts=None,
                        meta={"iceberg_display_qty": display_qty, "child": i + 1, "children": n},
                    )
                )

        elif method == "POV":
            # POV: participation-of-volume planning
            # We'll model as repeating chunks sized by expected flow.
            # Broker can implement real POV if supported; otherwise approximate as timed slices.
            participation = _clamp(pov_participation_rate, 0.01, 0.50)
            expected_flow_per_min = max(1.0, avg_minute_vol)
            chunk_qty = max(1, int(math.ceil(expected_flow_per_min * participation)))
            n = max(1, int(math.ceil(qty_i / chunk_qty)))
            duration_sec = max(60.0, _safe_float(self.cfg.get("pov_minutes", 6.0), 6.0) * 60.0)
            remaining = qty_i
            for i in range(n):
                q_i = min(chunk_qty, remaining)
                remaining -= q_i
                start_i = now + (duration_sec * i / n)
                end_i = now + (duration_sec * (i + 1) / n)
                children.append(
                    ExecutionChildOrder(
                        qty=q_i,
                        order_type=order_type,
                        limit_price=limit_price,
                        tif="DAY",
                        start_ts=start_i,
                        end_ts=end_i,
                        meta={"chunk": i + 1, "chunks": n, "algo": "POV", "participation": participation},
                    )
                )

        # Estimated slippage: simple heuristic based on spread + urgency + method
        est_slip = 0.0
        if sbps is not None:
            # crossing spread costs ~ half spread (marketable limit) to full spread (market), but we use marketable limits
            est_slip += 0.50 * sbps
        if urgent:
            est_slip += _safe_float(self.cfg.get("urgent_slippage_add_bps", 1.0), 1.0)
        if method in ("TWAP", "VWAP", "POV"):
            # slicing reduces expected slippage a bit
            est_slip *= _safe_float(self.cfg.get("algo_slippage_multiplier", 0.80), 0.80)
        if method == "ICEBERG":
            est_slip *= _safe_float(self.cfg.get("iceberg_slippage_multiplier", 0.85), 0.85)

        # Cap est slip at hard limit * 2 (just heuristic)
        est_slip = float(_clamp(est_slip, 0.0, hard_max_slippage_bps * 2.0))

        reason = " | ".join(reason_parts)

        plan_meta = {
            "symbol": symbol,
            "side": side_u,
            "expected_price": expected_price_f,
            "bid": bid_f,
            "ask": ask_f,
            "mid": mid_f,
            "last": last_f,
            "spread_bps": sbps,
            "is_wide_spread": is_wide_spread,
            "avg_minute_volume": avg_minute_vol,
            "volatility": volatility,
            "urgent": urgent,
        }

        return ExecutionPlan(
            method=method,
            order_type=order_type,
            qty=qty_i,
            limit_price=limit_price,
            children=children,
            est_slippage_bps=est_slip,
            hard_max_slippage_bps=hard_max_slippage_bps,
            reason=reason,
            meta=plan_meta,
        )


# Backwards-compatible alias
ExecutionAlphaModule = ExecutionAlpha
