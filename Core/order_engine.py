from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

from Core.compliance import Signal, enforce_signals_only, get_execution_mode


@dataclass
class OrderIntent:
    symbol: str
    side: str
    qty: int
    strategy: str
    meta: Dict[str, Any]


class OrderEngine:
    """
    SIGNAL-ONLY orchestrator (tool mode).

    This class is retained for API compatibility with earlier "place_order" wiring,
    but it NEVER submits orders to a broker and it NEVER simulates fills.

    Instead, it runs the full gate pipeline and returns a structured SIGNAL payload:
      eligibility_mask -> event_blackouts -> execution_safe_mode -> trade_throttle
      -> portfolio_constraints -> (execution alpha optional) -> SIGNAL OUTPUT

    You can plug in your existing modules here without changing their logic.
    """

    def __init__(
        self,
        *,
        eligibility_mask: Optional[Any] = None,
        event_blackouts: Optional[Any] = None,
        safe_mode: Optional[Any] = None,
        trade_throttle: Optional[Any] = None,
        portfolio_constraints: Optional[Any] = None,
        execution_alpha: Optional[Any] = None,
        signal_writer: Optional[Any] = None,
    ) -> None:
        self.eligibility_mask = eligibility_mask
        self.event_blackouts = event_blackouts
        self.safe_mode = safe_mode
        self.trade_throttle = trade_throttle
        self.portfolio_constraints = portfolio_constraints
        self.execution_alpha = execution_alpha
        self.signal_writer = signal_writer

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        strategy: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Backward-compatible entrypoint.

        Returns a SIGNAL payload like:
          {"status": "SIGNAL_ONLY", "signal": {...}, "trace": [...], "id": "..."}
        """
        enforce_signals_only(context="OrderEngine.place_order")
        meta = meta or {}
        intent = OrderIntent(symbol=symbol, side=side, qty=int(qty), strategy=strategy, meta=meta)
        return self._run_pipeline(intent)

    def _run_pipeline(self, intent: OrderIntent) -> Dict[str, Any]:
        t0 = time.time()
        trace: List[Dict[str, Any]] = []

        def _step(name: str, fn: Optional[Any], payload: Dict[str, Any]) -> Dict[str, Any]:
            if fn is None:
                trace.append({"step": name, "status": "SKIPPED"})
                return payload
            try:
                out = fn(payload)
                trace.append({"step": name, "status": "OK"})
                return out if isinstance(out, dict) else payload
            except Exception as e:
                trace.append({"step": name, "status": "ERROR", "error": str(e)})
                # In signals-only mode, we do not crash the whole tool; we return a BLOCKED signal.
                payload["blocked"] = True
                payload.setdefault("reasons", []).append(f"{name}_error:{e}")
                return payload

        payload: Dict[str, Any] = {
            "symbol": intent.symbol,
            "side": intent.side,
            "qty": intent.qty,
            "strategy": intent.strategy,
            "meta": intent.meta,
            "blocked": False,
            "reasons": [],
        }

        payload = _step("eligibility_mask", self.eligibility_mask, payload)
        payload = _step("event_blackouts", self.event_blackouts, payload)
        payload = _step("execution_safe_mode", self.safe_mode, payload)
        payload = _step("trade_throttle", self.trade_throttle, payload)
        payload = _step("portfolio_constraints", self.portfolio_constraints, payload)

        # Optional planner (still signals-only)
        payload = _step("execution_alpha_plan", self.execution_alpha, payload)

        # Build final signal
        signal = Signal(
            symbol=intent.symbol,
            side=intent.side,
            qty=intent.qty,
            strategy_id=intent.strategy,
            confidence=float(payload.get("confidence", 0.5) or 0.5),
            rationale=str(payload.get("rationale", "") or ""),
            meta={
                **(intent.meta or {}),
                "blocked": bool(payload.get("blocked")),
                "reasons": payload.get("reasons", []),
                "trace": trace,
            },
        )

        out = {
            "status": "SIGNAL_ONLY",
            "id": str(uuid.uuid4()),
            "ts": time.time(),
            "elapsed_ms": int((time.time() - t0) * 1000),
            "execution_mode": get_execution_mode(),
            "signal": signal.to_dict(),
            "trace": trace,
        }

        # Optional: write signal to disk if a writer is provided
        if self.signal_writer is not None:
            try:
                self.signal_writer(out)
            except Exception as e:
                out.setdefault("warnings", []).append(f"signal_writer_failed:{e}")

        return out
