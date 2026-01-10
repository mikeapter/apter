from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .trade_logger import TradeLogger
from .tca_engine import TCAEngine
from .degradation import DegradationMonitor, DegradationThresholds, DegradationAction


def _resolve_path(repo_root: Path, rel: str) -> Path:
    return (Path(repo_root) / rel).resolve()


@dataclass
class MonitoringConfig:
    trade_log_relpath: str = "Data/Logs/trades.jsonl"
    reports_dir_relpath: str = "Data/Reports"
    safe_mode_state_relpath: str = "Config/execution_safe_mode_state.json"
    slippage_state_relpath: str = "Config/slippage_state.json"
    thresholds: Optional[Dict[str, Any]] = None
    tca_monthly: bool = True
    tca_monthly_min_trades: int = 30


class MonitoringManager:
    def __init__(self, *, repo_root: Path, config_path: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root)

        cfg = MonitoringConfig()
        if config_path is not None and Path(config_path).exists():
            data = yaml.safe_load(Path(config_path).read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                for k, v in data.items():
                    if hasattr(cfg, k):
                        setattr(cfg, k, v)
        self.cfg = cfg

        self.trade_log_path = _resolve_path(self.repo_root, cfg.trade_log_relpath)
        self.reports_dir = _resolve_path(self.repo_root, cfg.reports_dir_relpath)
        self.safe_mode_state_path = _resolve_path(self.repo_root, cfg.safe_mode_state_relpath)
        self.slippage_state_path = _resolve_path(self.repo_root, cfg.slippage_state_relpath)

        self.logger = TradeLogger(repo_root=self.repo_root, path=self.trade_log_path)
        self.tca = TCAEngine(trade_log_path=self.trade_log_path)

        th = DegradationThresholds()
        if isinstance(cfg.thresholds, dict):
            for k, v in cfg.thresholds.items():
                if hasattr(th, k):
                    try:
                        setattr(th, k, v)
                    except Exception:
                        pass

        self.degradation = DegradationMonitor(
            trade_log_path=self.trade_log_path,
            execution_safe_mode_state_path=self.safe_mode_state_path,
            slippage_state_path=self.slippage_state_path,
            thresholds=th,
        )

    def log_order_result(
        self,
        *,
        symbol: str,
        side: str,
        qty: int,
        strategy: str,
        meta: Dict[str, Any],
        result: Dict[str, Any],
        started_ts: Optional[float] = None,
        broker: Optional[str] = None,
        venue: Optional[str] = None,
        order_type: Optional[str] = None,
    ) -> None:
        self.logger.log_from_result(
            symbol=symbol,
            side=side,
            qty=qty,
            strategy=strategy,
            meta=meta or {},
            result=result or {},
            started_ts=started_ts,
            broker=broker,
            venue=venue,
            order_type=order_type,
        )

    def check_and_apply_degradation(self) -> DegradationAction:
        action = self.degradation.evaluate()
        self.degradation.apply(action)
        return action

    def write_monthly_tca_report(self, month: Optional[str] = None) -> Path:
        return self.tca.write_monthly_report(out_dir=self.reports_dir, month=month)


class MonitoringOrderExecutor:
    """
    Universal wrapper that logs results for ANY executor.

    Works with both of your common signatures:
      1) place_order(symbol, side, qty, strategy, meta=...)
      2) place_order(strategy_id=..., symbol=..., side=..., qty=..., type=..., meta=...)
    """

    def __init__(self, *, inner: Any, monitor: MonitoringManager, broker_name: Optional[str] = None) -> None:
        self.inner = inner
        self.monitor = monitor
        self.broker_name = broker_name or getattr(inner, "name", None) or inner.__class__.__name__

    def place_order(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        import time

        symbol = kwargs.get("symbol") if "symbol" in kwargs else (args[0] if len(args) > 0 else "")
        side = kwargs.get("side") if "side" in kwargs else (args[1] if len(args) > 1 else "")
        qty = kwargs.get("qty") if "qty" in kwargs else (args[2] if len(args) > 2 else 0)

        strategy = kwargs.get("strategy") or kwargs.get("strategy_id") or (args[3] if len(args) > 3 else None) or "UNKNOWN"

        meta = kwargs.get("meta") if "meta" in kwargs else None
        if meta is None:
            meta = args[-1] if args and isinstance(args[-1], dict) else {}
        if isinstance(meta, dict):
            meta.setdefault("decision_ts", time.time())

        t0 = time.time()
        try:
            res = self.inner.place_order(*args, **kwargs)
        except Exception as e:
            res = {"status": "ERROR", "reason": f"EXCEPTION:{type(e).__name__}:{e}", "symbol": str(symbol), "side": str(side), "qty": qty, "strategy": str(strategy)}

        self.monitor.log_order_result(
            symbol=str(symbol),
            side=str(side),
            qty=int(qty) if str(qty).lstrip("-").isdigit() else 0,
            strategy=str(strategy),
            meta=meta if isinstance(meta, dict) else {},
            result=res if isinstance(res, dict) else {"status": "UNKNOWN", "raw": str(res)},
            started_ts=t0,
            broker=self.broker_name,
            venue=(meta or {}).get("venue") if isinstance(meta, dict) else None,
            order_type=(meta or {}).get("order_type") if isinstance(meta, dict) else None,
        )
        return res
