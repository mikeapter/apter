from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, List


@dataclass
class OrderIntent:
    symbol: str
    side: str
    qty: int
    strategy: str
    meta: Dict[str, Any]


class OrderEngine:
    """
    Final integration orchestrator (Step 22):
      eligibility_mask -> event_blackouts -> execution_safe_mode -> trade_throttle
      -> portfolio_constraints -> (execution alpha optional) -> broker/paper fill

    This file is built to be "signature-safe" against your existing module APIs.
    It NEVER crashes the runner; it returns a structured dict with decision_trace.
    """

    def __init__(
        self,
        *,
        mode: str,
        eligibility_mask: Any = None,
        event_blackouts: Any = None,
        execution_safe_mode: Any = None,
        trade_throttle: Any = None,
        portfolio_constraints: Any = None,
        execution_alpha: Any = None,
        broker: Any = None,
        logger: Any = None,
    ) -> None:
        self.mode = str(mode).upper()
        self.eligibility_mask = eligibility_mask
        self.event_blackouts = event_blackouts
        self.execution_safe_mode = execution_safe_mode
        self.trade_throttle = trade_throttle
        self.portfolio_constraints = portfolio_constraints
        self.execution_alpha = execution_alpha
        self.broker = broker
        self.log = logger

    # ---------------- helpers ----------------

    def _now(self) -> float:
        return float(time.time())

    def _mk_run_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def _trace(self, trace: List[Dict[str, Any]], module: str, allowed: bool, reason: str, extras: Optional[Dict[str, Any]] = None) -> None:
        item = {"module": module, "allowed": bool(allowed), "reason": str(reason)}
        if extras:
            item["extras"] = extras
        trace.append(item)

    def _block(self, *, run_id: str, symbol: str, side: str, qty: int, strategy: str, reason: str, trace: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "status": "BLOCKED",
            "symbol": symbol,
            "strategy_id": strategy,
            "side": side,
            "qty": int(qty),
            "reason": str(reason),
            "decision_trace": trace,
            "run_id": run_id,
            "mode": self.mode,
        }

    def _filled(self, *, run_id: str, symbol: str, side: str, qty: int, strategy: str, fill_price: float, trace: List[Dict[str, Any]], extras: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        out = {
            "status": "PAPER_FILLED" if self.mode in ("PAPER", "SIM") else "FILLED",
            "symbol": symbol,
            "strategy_id": strategy,
            "side": side,
            "qty": int(qty),
            "fill_price": float(fill_price),
            "reason": "OK",
            "decision_trace": trace,
            "run_id": run_id,
            "mode": self.mode,
        }
        if extras:
            out["extras"] = extras
        return out

    def _get_quote(self, symbol: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        # Prefer meta-provided quote, then broker quote, then safe default.
        q = meta.get("quote")
        if isinstance(q, dict) and any(k in q for k in ("bid", "ask", "mid", "last")):
            return q

        if self.broker is not None and hasattr(self.broker, "get_quote"):
            try:
                qb = self.broker.get_quote(symbol)
                if isinstance(qb, dict):
                    return qb
            except Exception:
                pass

        # fallback quote (lets pipeline run)
        last = float(meta.get("last_price") or 100.00)
        bid = float(meta.get("bid") or (last - 0.01))
        ask = float(meta.get("ask") or (last + 0.01))
        mid = float(meta.get("mid") or ((bid + ask) / 2.0))
        return {"bid": bid, "ask": ask, "mid": mid, "last": last}

    # ---------------- public API ----------------

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        qty: int,
        strategy_id: str,
        regime: str,
        regime_confidence: float,
        urgency: str = "NORMAL",
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        run_id = self._mk_run_id()
        trace: List[Dict[str, Any]] = []

        symbol_u = str(symbol).upper().strip()
        side_u = str(side).upper().strip()
        strategy_u = str(strategy_id).upper().strip()
        regime_u = str(regime).upper().strip()

        try:
            qty_i = int(qty)
        except Exception:
            qty_i = 0
        qty_i = max(0, qty_i)

        meta = meta or {}
        meta = dict(meta)  # copy so we can safely mutate
        meta.setdefault("run_id", run_id)
        meta.setdefault("mode", self.mode)
        meta.setdefault("regime", regime_u)
        meta.setdefault("regime_confidence", float(regime_confidence))

        if qty_i <= 0:
            self._trace(trace, "sanity", False, "qty<=0")
            return self._block(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, reason="QTY_INVALID", trace=trace)

        quote = self._get_quote(symbol_u, meta)
        meta["quote"] = quote

        # 1) Eligibility mask
        if self.eligibility_mask is not None and hasattr(self.eligibility_mask, "decide"):
            try:
                d = self.eligibility_mask.decide(regime=regime_u, strategy=strategy_u, confidence=float(regime_confidence))
                allowed = bool(getattr(d, "allowed", False))
                reason = str(getattr(d, "reason", "blocked"))
                self._trace(trace, "eligibility_mask", allowed, reason, {"regime": getattr(d, "regime", regime_u), "confidence": getattr(d, "confidence", None)})
                if not allowed:
                    return self._block(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, reason=reason, trace=trace)
            except Exception as e:
                self._trace(trace, "eligibility_mask", False, f"blocked: {e}")
                return self._block(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, reason="ELIGIBILITY_ERROR", trace=trace)

        # 2) Event blackouts
        if self.event_blackouts is not None and hasattr(self.event_blackouts, "pre_trade"):
            try:
                d = self.event_blackouts.pre_trade(
                    symbol=symbol_u,
                    side=side_u,
                    qty=qty_i,
                    strategy=strategy_u,
                    quote=quote,
                    meta=meta,
                    now_ts=self._now(),
                )
                allowed = bool(getattr(d, "allowed", False))
                reason = str(getattr(d, "reason", "blocked"))
                extras = {"action": getattr(d, "action", None), "tags": getattr(d, "tags", None)}
                self._trace(trace, "event_blackouts", allowed, reason, extras)
                if not allowed:
                    return self._block(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, reason=reason, trace=trace)

                # if blackout suggests forcing safe mode level, pass into meta
                fsl = getattr(d, "force_safe_mode_level", None)
                if fsl:
                    meta["force_safe_mode_level"] = str(fsl).upper()
            except Exception as e:
                self._trace(trace, "event_blackouts", False, f"blocked: {e}")
                return self._block(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, reason="EVENT_BLACKOUTS_ERROR", trace=trace)

        # 3) Execution safe mode
        size_mult = 1.0
        cooldown_mult = 1.0
        max_trades_mult = 1.0
        if self.execution_safe_mode is not None and hasattr(self.execution_safe_mode, "pre_trade"):
            try:
                d = self.execution_safe_mode.pre_trade(
                    symbol=symbol_u,
                    side=side_u,
                    qty=qty_i,
                    quote=quote,
                    meta=meta,
                    now_ts=self._now(),
                )
                size_mult = float(getattr(d, "size_multiplier", 1.0) or 1.0)
                cooldown_mult = float(getattr(d, "cooldown_multiplier", 1.0) or 1.0)
                max_trades_mult = float(getattr(d, "max_trades_multiplier", 1.0) or 1.0)

                # tighten qty if required
                if size_mult < 1.0 and qty_i > 0:
                    new_qty = max(1, int(qty_i * size_mult))
                    if new_qty != qty_i:
                        self._trace(trace, "execution_safe_mode", True, "ok", {"size_mult": size_mult, "qty_before": qty_i, "qty_after": new_qty})
                        qty_i = new_qty
                    else:
                        self._trace(trace, "execution_safe_mode", True, "ok", {"size_mult": size_mult})
                else:
                    self._trace(trace, "execution_safe_mode", True, "ok", {"size_mult": size_mult})

                # If safe mode blocks new entries, block unless explicit exit flag
                if bool(getattr(d, "block_new_entries", False)) and not bool(meta.get("is_exit")):
                    return self._block(
                        run_id=run_id,
                        symbol=symbol_u,
                        side=side_u,
                        qty=qty_i,
                        strategy=strategy_u,
                        reason="SAFE_MODE_BLOCK_NEW_ENTRIES",
                        trace=trace,
                    )

            except Exception as e:
                self._trace(trace, "execution_safe_mode", False, f"blocked: safe mode error: {e}")
                return self._block(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, reason="SAFE_MODE_ERROR", trace=trace)

        # 4) Trade throttle
        if self.trade_throttle is not None and hasattr(self.trade_throttle, "can_trade"):
            try:
                d = self.trade_throttle.can_trade(
                    regime=regime_u,
                    urgency=str(urgency).upper(),
                    max_trades_multiplier=max_trades_mult,
                    cooldown_multiplier=cooldown_mult,
                )
                allowed = bool(getattr(d, "allowed", False))
                reason = str(getattr(d, "reason", "blocked"))
                self._trace(trace, "trade_throttle", allowed, reason, {"regime": regime_u})
                if not allowed:
                    return self._block(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, reason=reason, trace=trace)
            except Exception as e:
                self._trace(trace, "trade_throttle", False, f"blocked: {e}")
                return self._block(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, reason="THROTTLE_ERROR", trace=trace)

        # 5) Portfolio constraints (expects an ORDER-LIKE object as first arg)
        if self.portfolio_constraints is not None and hasattr(self.portfolio_constraints, "check_pre_trade"):
            try:
                order_like = OrderIntent(symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, meta=meta)

                # PortfolioConstraintsGate.check_pre_trade(order, *, meta=None, price=None)
                mid = quote.get("mid") or quote.get("last") or 0.0
                d = self.portfolio_constraints.check_pre_trade(order_like, meta=meta, price=float(mid) if mid else None)

                allowed = bool(getattr(d, "allowed", False))
                reason = str(getattr(d, "reason", "blocked"))
                self._trace(trace, "portfolio_constraints", allowed, reason, {"action": getattr(d, "action", None)})

                if not allowed:
                    return self._block(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, reason=reason, trace=trace)

                # optional qty cap
                qty_cap = getattr(d, "qty_cap", None)
                if qty_cap is not None:
                    try:
                        qty_i = min(qty_i, int(qty_cap))
                    except Exception:
                        pass

            except Exception as e:
                self._trace(trace, "portfolio_constraints", False, f"blocked: portfolio error: {e}")
                return self._block(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, reason="PORTFOLIO_ERROR", trace=trace)

        # 6) Execution alpha (optional) – for now we still paper-fill deterministically
        if self.execution_alpha is not None and hasattr(self.execution_alpha, "build_plan"):
            try:
                _ = self.execution_alpha.build_plan(symbol=symbol_u, side=side_u, qty=qty_i, quote=quote, meta=meta)
                self._trace(trace, "execution_alpha", True, "ok")
            except Exception as e:
                # Not fatal in PAPER; fall back to simple fill
                self._trace(trace, "execution_alpha", True, f"fallback: {e}")

        # 7) Broker submit / paper fill
        fill_price = float(quote.get("mid") or quote.get("last") or 0.0) or 100.0
        if self.broker is not None and hasattr(self.broker, "submit_order") and self.mode not in ("PAPER", "SIM"):
            try:
                resp = self.broker.submit_order(symbol=symbol_u, side=side_u, qty=qty_i, meta=meta)
                if isinstance(resp, dict) and resp.get("fill_price"):
                    fill_price = float(resp["fill_price"])
                self._trace(trace, "broker", True, "submitted")
                return self._filled(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, fill_price=fill_price, trace=trace, extras={"broker_resp": resp})
            except Exception as e:
                self._trace(trace, "broker", False, f"blocked: {e}")
                return self._block(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, reason="BROKER_ERROR", trace=trace)

        self._trace(trace, "paper_fill", True, "ok", {"fill_price": fill_price})
        return self._filled(run_id=run_id, symbol=symbol_u, side=side_u, qty=qty_i, strategy=strategy_u, fill_price=fill_price, trace=trace)

