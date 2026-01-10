# (PASTE YOUR FULL EXISTING FILE CONTENT, WITH THESE STEP 19 CHANGES INCLUDED)
# Since you asked for copy/paste-ready: here is the updated file as-is.

from dataclasses import dataclass
from typing import Any, Dict, Optional

from Core.adverse_selection import AdverseSelectionDecision, AdverseSelectionModule
from Core.eligibility_mask import EligibilityDecision, EligibilityMask
from Core.event_blackouts import EventBlackoutDecision, EventBlackoutGate
from Core.portfolio_constraints import PortfolioConstraintsGate, PortfolioConstraintsDecision
from Core.execution_alpha import ExecutionAlphaModule
from Core.execution_safe_mode import ExecutionSafeModeDecision, ExecutionSafeModeModule
from Core.slippage_tracker import SlippageDecision, SlippageTracker
from Core.trade_throttle import ThrottleDecision, TradeThrottle


@dataclass
class OrderRequest:
    symbol: str
    side: str  # BUY/SELL
    qty: int
    strategy: str
    meta: Dict[str, Any]


class OrderExecutor:
    """
    Order path with layered gates:

    Step 09: Strategy Eligibility Mask
    Step 12: Trade throttle
    Step 15: Execution alpha selection
    Step 16: Adverse selection module
    Step 17: Execution safe mode
    Step 18: event + liquidity blackout rules (macro/earnings/open-close/shocks)
    Step 19: portfolio constraints (concentration/leverage/VaR/DD modes)
    """

    def __init__(
        self,
        broker: Any,
        *,
        eligibility_mask: Optional[EligibilityMask] = None,  # <<< STEP 09
        throttle: Optional[TradeThrottle] = None,  # <<< STEP 12
        slippage_tracker: Optional[SlippageTracker] = None,  # <<< STEP 15
        execution_alpha: Optional[ExecutionAlphaModule] = None,  # <<< STEP 15
        adverse_selection: Optional[AdverseSelectionModule] = None,  # <<< STEP 16
        safe_mode: Optional[ExecutionSafeModeModule] = None,  # <<< STEP 17
        event_blackout: Optional[EventBlackoutGate] = None,  # <<< STEP 18
        portfolio_constraints: Optional[PortfolioConstraintsGate] = None,  # <<< STEP 19
        mode: str = "PAPER",
        logger: Optional[Any] = None,
    ):
        self.broker = broker
        self.eligibility_mask = eligibility_mask
        self.throttle = throttle
        self.slippage_tracker = slippage_tracker
        self.execution_alpha = execution_alpha
        self.adverse_selection = adverse_selection
        self.safe_mode = safe_mode
        self.event_blackout = event_blackout
        self.portfolio_constraints = portfolio_constraints
        self.mode = str(mode).upper()
        self.log = logger

    def place_order(self, symbol: str, side: str, qty: int, strategy: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        meta = meta or {}
        meta.setdefault("mode", self.mode)
        symbol = str(symbol).upper()
        side = str(side).upper()
        strategy = str(strategy).upper()
        qty = int(qty)

        # Quote
        quote = self.broker.get_quote(symbol)
        try:
            meta["quote"] = {"mid": float(getattr(quote, "mid", 0.0)), "last": float(getattr(quote, "last", 0.0))}
        except Exception:
            meta["quote"] = {}

        regime = meta.get("regime", meta.get("regime_label", "UNKNOWN"))

        # STEP 15: slippage pre-trade pause / block
        slip_dec: Optional[SlippageDecision] = None
        if self.slippage_tracker is not None:
            slip_dec = self.slippage_tracker.pre_trade_check(symbol=symbol, side=side, qty=qty, meta=meta)
            if not slip_dec.allowed:
                return {
                    "status": "BLOCKED",
                    "reason": f"SLIPPAGE:{slip_dec.reason}",
                    "symbol": symbol,
                    "strategy": strategy,
                    "regime": str(regime).upper(),
                    "slippage": slip_dec.__dict__,
                }

        # STEP 09: eligibility mask
        elig_dec: Optional[EligibilityDecision] = None
        if self.eligibility_mask is not None:
            elig_dec = self.eligibility_mask.is_allowed(strategy=strategy, regime=str(regime).upper(), symbol=symbol)
            if not elig_dec.allowed:
                return {
                    "status": "BLOCKED",
                    "reason": f"ELIGIBILITY:{elig_dec.reason}",
                    "symbol": symbol,
                    "strategy": strategy,
                    "regime": str(regime).upper(),
                    "eligibility": elig_dec.__dict__,
                }

        # STEP 18: event + liquidity blackouts
        eb: Optional[EventBlackoutDecision] = None
        if self.event_blackout is not None:
            eb = self.event_blackout.check(symbol=symbol, now_ts=meta.get("now_ts"), meta=meta)
            if eb.action in ("BLOCK", "HALT"):
                return {
                    "status": "BLOCKED",
                    "reason": f"EVENT_BLACKOUT:{eb.reason}",
                    "symbol": symbol,
                    "strategy": strategy,
                    "regime": str(regime).upper(),
                    "event_blackout": {"action": eb.action, "reason": eb.reason, "tags": eb.tags},
                }
            if eb.action == "REDUCE_ONLY":
                meta["_reduce_only"] = True

        # STEP 17: execution safe mode
        safe_dec: Optional[ExecutionSafeModeDecision] = None
        if self.safe_mode is not None:
            safe_dec = self.safe_mode.evaluate(symbol=symbol, side=side, qty=qty, meta=meta)
            if safe_dec.block and not bool(meta.get("_reduce_only", False)):
                return {
                    "status": "BLOCKED",
                    "reason": f"SAFE_MODE:{safe_dec.reason}",
                    "symbol": symbol,
                    "strategy": strategy,
                    "regime": str(regime).upper(),
                    "safe_mode": safe_dec.__dict__,
                    "event_blackout": {"action": eb.action, "reason": eb.reason, "tags": eb.tags} if eb else None,
                }
            if safe_dec.qty_multiplier is not None and safe_dec.qty_multiplier < 1.0:
                qty = max(1, int(qty * safe_dec.qty_multiplier))
                meta["_safe_mode_resized"] = True

        # STEP 12: trade throttle (frequency/cooldowns)
        thr: Optional[ThrottleDecision] = None
        if self.throttle is not None:
            thr = self.throttle.check(symbol=symbol, strategy=strategy, regime=str(regime).upper(), now_ts=meta.get("now_ts"))
            if not thr.allowed and not bool(meta.get("_reduce_only", False)):
                return {
                    "status": "BLOCKED",
                    "reason": f"THROTTLE:{thr.reason}",
                    "symbol": symbol,
                    "strategy": strategy,
                    "regime": str(regime).upper(),
                    "throttle": thr.__dict__,
                    "safe_mode": safe_dec.__dict__ if safe_dec else None,
                    "event_blackout": {"action": eb.action, "reason": eb.reason, "tags": eb.tags} if eb else None,
                }

        # STEP 19: portfolio constraints gate (portfolio construction hard limits)
        if self.portfolio_constraints is not None:
            # Portfolio constraints should never block exits (de-risking).
            # If you have an exit flag elsewhere, set meta['is_exit']=True.
            pc_dec: PortfolioConstraintsDecision = self.portfolio_constraints.check_pre_trade(
                OrderRequest(symbol=symbol, side=side, qty=qty, strategy=strategy, meta=meta),
                meta=meta,
                price=float(getattr(quote, "mid", None) or getattr(quote, "last", None) or 0.0) or None,
            )
            if not pc_dec.allowed:
                return {
                    "status": "BLOCKED",
                    "reason": f"PORTFOLIO_CONSTRAINTS:{pc_dec.reason}",
                    "symbol": symbol,
                    "strategy": strategy,
                    "regime": str(regime).upper(),
                    "portfolio_constraints": {"action": pc_dec.action, "risk_multiplier": pc_dec.risk_multiplier, "details": pc_dec.details},
                    "safe_mode": safe_dec.__dict__ if safe_dec else None,
                    "event_blackout": {"action": eb.action, "reason": eb.reason, "tags": eb.tags} if eb else None,
                }
            if int(pc_dec.adjusted_qty) != int(qty):
                meta["_portfolio_resized"] = True
                meta["_portfolio_resize_reason"] = pc_dec.reason
                qty = int(pc_dec.adjusted_qty)

        # STEP 16: adverse selection pre-trade decision
        adv: Optional[AdverseSelectionDecision] = None
        if self.adverse_selection is not None:
            adv = self.adverse_selection.evaluate(symbol=symbol, side=side, qty=qty, quote=quote, meta=meta)
            meta["adverse_selection"] = adv.__dict__
            if adv.prefer_aggressive:
                meta["force_aggressive"] = True

        # STEP 15: execution alpha module picks method + plan
        if self.execution_alpha is None:
            # minimal fallback
            plan = {"method": "MARKETABLE_LIMIT", "limit_price": getattr(quote, "mid", getattr(quote, "last", None)), "slices": 1}
        else:
            plan = self.execution_alpha.build_plan(symbol=symbol, side=side, qty=qty, quote=quote, meta=meta)

        # execute (paper vs live)
        if self.mode == "PAPER":
            fill_price = float(getattr(quote, "mid", 0.0) or getattr(quote, "last", 0.0) or 0.0)
            result = {"status": "PAPER_FILLED", "symbol": symbol, "side": side, "qty": qty, "fill_price": fill_price, "plan": plan, "meta": meta}
        else:
            # delegate to broker
            result = self.broker.submit_order(symbol=symbol, side=side, qty=qty, plan=plan, meta=meta)

        # update slippage tracker post-fill
        if self.slippage_tracker is not None:
            try:
                self.slippage_tracker.post_trade_update(
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    expected_price=float(getattr(quote, "mid", 0.0) or getattr(quote, "last", 0.0) or 0.0),
                    fill_price=float(result.get("fill_price", 0.0) or 0.0),
                    meta=meta,
                )
            except Exception:
                pass

        return result
