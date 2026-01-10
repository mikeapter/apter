from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional


def _utc_ts() -> float:
    return time.time()


def _safe_json(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


@dataclass(frozen=True)
class AuditEvent:
    ts: float
    event: str
    run_id: str
    mode: str
    strategy_id: Optional[str] = None
    symbol: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None


class AuditLogger:
    def __init__(self, *, repo_root: Path, retention_years: int = 7) -> None:
        self.repo_root = Path(repo_root)
        self.retention_years = int(retention_years)
        self.audit_root = self.repo_root / "Data" / "Audit"
        self.audit_root.mkdir(parents=True, exist_ok=True)
        self.hostname = socket.gethostname()

    def _daily_path(self, ts: Optional[float] = None) -> Path:
        ts = _utc_ts() if ts is None else float(ts)
        ymd = time.strftime("%Y%m%d", time.gmtime(ts))
        day_dir = self.audit_root / ymd
        day_dir.mkdir(parents=True, exist_ok=True)
        return day_dir / "events.jsonl"

    def log(
        self,
        event: str,
        *,
        run_id: str,
        mode: str,
        strategy_id: Optional[str] = None,
        symbol: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        ts: Optional[float] = None,
    ) -> None:
        ev = AuditEvent(
            ts=_utc_ts() if ts is None else float(ts),
            event=str(event),
            run_id=str(run_id),
            mode=str(mode).upper(),
            strategy_id=strategy_id,
            symbol=symbol,
            payload=_safe_json(payload) if payload is not None else None,
        )
        path = self._daily_path(ev.ts)
        record = asdict(ev)
        record["host"] = self.hostname
        record["pid"] = os.getpid()

        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
