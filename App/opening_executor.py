from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from Core.compliance import enforce_signals_only
from Core.order_engine import OrderEngine


class OpeningExecutor:
    """
    Signals-only "opening" decision runner.

    - Pulls quotes from DataRedundancyManager (tool-safe)
    - Applies simple decision logic (placeholder)
    - Emits SIGNAL payload via OrderEngine (never executes trades)
    - Writes JSON to Platform/runtime/signals
    """

    def __init__(
        self,
        *,
        data: Any,
        order_exec: Optional[Any],
        repo_root: Path,
        config_path: Path,
    ) -> None:
        self.data = data
        self.order_exec = order_exec  # intentionally unused (signals-only)
        self.repo_root = Path(repo_root)
        self.config_path = Path(config_path)

        enforce_signals_only(context="OpeningExecutor.__init__")

        self.cfg = self._load_cfg(self.config_path)
        self.engine = OrderEngine()

    def _load_cfg(self, p: Path) -> Dict[str, Any]:
        # Strong defaults with correct types
        cfg: Dict[str, Any] = {
            "universe": {"symbols": ["SPY"]},
            "strategy": {"id": "opening_v1", "default_qty": 1},
            "output": {"signals_dir": "Platform/runtime/signals", "file_prefix": "signal"},
            "explain": {"include_trace": True},
        }

        if not p.exists():
            return cfg

        txt = p.read_text(encoding="utf-8", errors="ignore").splitlines()

        section: Optional[str] = None
        for raw in txt:
            line = raw.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue

            # top-level section
            if not line.startswith(" "):
                section = line.split(":", 1)[0].strip()
                if section not in cfg:
                    cfg[section] = {}
                continue

            s = line.strip()

            # --- universe.symbols list handling ---
            if section == "universe":
                # if we see "symbols:" with no value, force list init
                if s.startswith("symbols:"):
                    after = s.split(":", 1)[1].strip()
                    if after:
                        # allow inline list like [AAPL, MSFT]
                        if after.startswith("[") and after.endswith("]"):
                            inner = after[1:-1].strip()
                            items = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()]
                            cfg["universe"]["symbols"] = items if items else []
                        else:
                            cfg["universe"]["symbols"] = [after.strip().strip('"').strip("'")]
                    else:
                        cfg["universe"]["symbols"] = []
                    continue

                # list item lines "- AAPL"
                if s.startswith("-"):
                    sym = s.lstrip("-").strip().strip('"').strip("'")
                    if "symbols" not in cfg["universe"] or not isinstance(cfg["universe"]["symbols"], list):
                        cfg["universe"]["symbols"] = []
                    cfg["universe"]["symbols"].append(sym)
                    continue

            # --- generic key: value parsing for other sections ---
            if ":" in s and section:
                k, v = s.split(":", 1)
                k = k.strip()
                v = v.strip()

                # If blank value, ignore (or keep defaults)
                if v == "":
                    continue

                # strip quotes
                v2 = v.strip('"').strip("'")

                # cast
                if v2.lower() in ("true", "false"):
                    val: Any = v2.lower() == "true"
                else:
                    try:
                        val = float(v2) if "." in v2 else int(v2)
                    except Exception:
                        val = v2

                if section not in cfg or not isinstance(cfg[section], dict):
                    cfg[section] = {}
                cfg[section][k] = val

        # Safety: ensure correct type for universe.symbols
        if "universe" not in cfg or not isinstance(cfg["universe"], dict):
            cfg["universe"] = {"symbols": ["SPY"]}
        if "symbols" not in cfg["universe"] or not isinstance(cfg["universe"]["symbols"], list):
            cfg["universe"]["symbols"] = ["SPY"]

        return cfg

    def _decide(self, quote: Dict[str, float]) -> Dict[str, Any]:
        """
        Placeholder decision logic:
        - BUY if last >= mid
        - SELL otherwise
        Replace this with your existing algorithm outputs.
        """
        last = float(quote.get("last", 0.0))
        mid = float(quote.get("mid", 0.0))
        if last >= mid:
            return {"side": "BUY", "confidence": 0.55, "rationale": "last>=mid"}
        return {"side": "SELL", "confidence": 0.55, "rationale": "last<mid"}

    def _write_signal(self, payload: Dict[str, Any]) -> None:
        out_cfg = self.cfg.get("output") or {}
        rel_dir = str(out_cfg.get("signals_dir", "Platform/runtime/signals"))
        prefix = str(out_cfg.get("file_prefix", "signal"))

        out_dir = (self.repo_root / rel_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"{prefix}_{ts}.json"
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def run_one_shot(self) -> Dict[str, Any]:
        enforce_signals_only(context="OpeningExecutor.run_one_shot")

        symbols = (self.cfg.get("universe") or {}).get("symbols") or ["SPY"]
        strategy_id = (self.cfg.get("strategy") or {}).get("id") or "opening_v1"
        default_qty = int((self.cfg.get("strategy") or {}).get("default_qty") or 1)

        results = []
        for sym in symbols:
            q = self.data.get_quote(sym)
            d = self._decide(q)

            meta = {
                "quote": q,
                "confidence": d.get("confidence", 0.5),
                "rationale": d.get("rationale", ""),
            }

            out = self.engine.place_order(
                sym,
                str(d.get("side", "BUY")),
                default_qty,
                strategy_id,
                meta=meta,
            )
            results.append(out)

            self._write_signal(out)

        return {"status": "OK", "count": len(results), "results": results}
