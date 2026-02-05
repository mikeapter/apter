from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


class ExecutionDisabledError(RuntimeError):
    """Raised when anything attempts to automate trade execution in this signals-only repo."""


class ExecutionMode:
    """Allowed runtime modes. Only TOOL is supported in this repo."""

    TOOL = "TOOL"  # signals-only; users execute independently

    # Reserved / intentionally unsupported (kept for clarity / future forks)
    PAPER = "PAPER"
    SIM = "SIM"
    LIVE = "LIVE"


def get_execution_mode() -> str:
    """Returns the configured execution mode (defaults to TOOL)."""
    mode = (os.getenv("BOTTRADER_EXECUTION_MODE") or os.getenv("BOT_EXECUTION_MODE") or ExecutionMode.TOOL).strip().upper()
    return mode or ExecutionMode.TOOL


def enforce_signals_only(context: str = "") -> None:
    """Hard-stop if someone tries to run this repo in anything other than TOOL mode."""
    mode = get_execution_mode()
    if mode != ExecutionMode.TOOL:
        raise ExecutionDisabledError(
            f"Signals-only enforcement: execution_mode={mode} is not supported. "
            f"This repo supports TOOL mode only. context={context}"
        )


def forbid_automated_execution(context: str = "") -> None:
    """Always raises. Use this in any broker/executor code path."""
    raise ExecutionDisabledError(f"Automated execution is disabled (signals-only repo). context={context}")


@dataclass
class Signal:
    """Standard signal envelope (what the tool outputs)."""

    symbol: str
    side: str  # BUY / SELL
    qty: int
    strategy_id: str
    confidence: float = 0.5
    rationale: str = ""
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "qty": int(self.qty),
            "strategy_id": self.strategy_id,
            "confidence": float(self.confidence),
            "rationale": str(self.rationale),
            "meta": self.meta or {},
            "execution_mode": get_execution_mode(),
        }
