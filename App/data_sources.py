from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class DataRedundancyManager:
    """
    Minimal data manager for signals-only mode.

    Reads Config/data_sources.yaml, but stays tool-safe:
    - no network calls required
    - provides stub quotes if no feed is connected
    """

    config_path: str

    def __post_init__(self) -> None:
        self._cfg = self._load_cfg(self.config_path)

    def _load_cfg(self, p: str) -> Dict[str, Any]:
        path = Path(p)
        if not path.exists():
            # Safe defaults
            return {
                "policy": {"allow_failover": True, "allow_synthetic_quote": True},
                "synthetic_quote_defaults": {"bid": 100.0, "ask": 100.02, "last": 100.01},
            }
        # Simple YAML-ish parser fallback: expect key/value-like JSON or minimal YAML.
        txt = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not txt:
            return {}
        # If user put JSON, allow it
        if txt.startswith("{"):
            return json.loads(txt)
        # Very small YAML reader (only what we need here)
        cfg: Dict[str, Any] = {}
        current_section: Optional[str] = None
        for raw in txt.splitlines():
            line = raw.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            if not line.startswith(" "):
                # section:
                if ":" in line:
                    k = line.split(":", 1)[0].strip()
                    current_section = k
                    cfg.setdefault(k, {})
                continue
            # indented key: value
            if ":" in line and current_section:
                k, v = line.strip().split(":", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                # try cast
                if v.lower() in ("true", "false"):
                    val: Any = v.lower() == "true"
                else:
                    try:
                        val = float(v) if "." in v else int(v)
                    except Exception:
                        val = v
                cfg[current_section][k] = val
        return cfg

    def get_quote(self, symbol: str) -> Dict[str, float]:
        """
        Tool-safe quote snapshot.
        Replace this with your real market data connection later.
        """
        defaults = (self._cfg.get("synthetic_quote_defaults") or {})
        bid = float(defaults.get("bid", 100.0))
        ask = float(defaults.get("ask", 100.02))
        last = float(defaults.get("last", (bid + ask) / 2.0))
        mid = (bid + ask) / 2.0
        return {"bid": bid, "ask": ask, "mid": mid, "last": last}
