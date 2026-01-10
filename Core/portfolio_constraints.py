# Core/portfolio_constraints.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from Core.decision import Decision


class MetaPortfolioProvider:
    def nav(self, meta: Dict[str, Any]) -> float:
        p = meta.get("portfolio", {}) if isinstance(meta.get("portfolio"), dict) else {}
        return float(p.get("nav", meta.get("nav", 0.0)))

    def positions(self, meta: Dict[str, Any]) -> list[Dict[str, Any]]:
        p = meta.get("portfolio", {}) if isinstance(meta.get("portfolio"), dict) else {}
        return list(p.get("positions", []) or [])

    def risk_metrics(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        p = meta.get("portfolio", {}) if isinstance(meta.get("portfolio"), dict) else {}
        rm = p.get("risk_metrics", {}) if isinstance(p.get("risk_metrics"), dict) else {}
        return dict(rm)

    @staticmethod
    def _pos_symbol(pos: Dict[str, Any]) -> str:
        return str(pos.get("symbol") or pos.get("ticker") or pos.get("asset") or "")

    @staticmethod
    def _pos_qty(pos: Dict[str, Any]) -> float:
        v = pos.get("qty", pos.get("quantity", pos.get("shares", 0)))
        try:
            return float(v)
        except Exception:
            return 0.0

    @staticmethod
    def _pos_price(pos: Dict[str, Any], fallback_price: float) -> float:
        v = pos.get("price", pos.get("avg_price", pos.get("mark", fallback_price)))
        try:
            return float(v)
        except Exception:
            return float(fallback_price)

    def symbol_exposure(self, meta: Dict[str, Any], symbol: str, fallback_price: float) -> float:
        exp = 0.0
        for p in self.positions(meta):
            if self._pos_symbol(p) != symbol:
                continue
            exp += abs(self._pos_qty(p) * self._pos_price(p, fallback_price))
        return exp

    def gross_exposure(self, meta: Dict[str, Any], fallback_price: float) -> float:
        exp = 0.0
        for p in self.positions(meta):
            exp += abs(self._pos_qty(p) * self._pos_price(p, fallback_price))
        return exp


class PortfolioConstraintsGate:
    def __init__(
        self,
        config: Dict[str, Any],
        meta_provider: Optional[MetaPortfolioProvider] = None,
        state_path: Optional[Path] = None,
    ) -> None:
        if "portfolio_constraints" in config and isinstance(config["portfolio_constraints"], dict):
            config = config["portfolio_constraints"]

        self.config: Dict[str, Any] = dict(config)
        self.meta_provider = meta_provider or MetaPortfolioProvider()

        self._state_path = state_path
        self._state: Dict[str, Any] = {}
        self._load_state()

        # Ensure expected sections exist
        self.config.setdefault("concentration", {})
        self.config.setdefault("leverage", {})
        self.config.setdefault("var_es", {})
        self.config.setdefault("drawdown", {})

    @classmethod
    def from_yaml(
        cls, cfg_path: str | Path, meta_provider: Optional[MetaPortfolioProvider] = None
    ) -> "PortfolioConstraintsGate":
        cfg_path = Path(cfg_path)
        with cfg_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        state_path = cfg_path.with_suffix(".state.json")
        return cls(config=config, meta_provider=meta_provider, state_path=state_path)

    def _load_state(self) -> None:
        if not self._state_path:
            self._state = {}
            return
        try:
            if self._state_path.exists():
                self._state = json.loads(self._state_path.read_text(encoding="utf-8"))
            else:
                self._state = {}
        except Exception:
            self._state = {}

    def _save_state(self) -> None:
        if not self._state_path:
            return
        try:
            self._state_path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def _floor_qty(x: float) -> int:
        if x <= 0:
            return 0
        return int(x + 1e-9)

    def check_pre_trade(self, order: Any, meta: Dict[str, Any], price: float) -> Decision:
        symbol = str(getattr(order, "symbol"))
        side = str(getattr(order, "side", "BUY")).upper()
        requested_qty = int(getattr(order, "qty"))
        price = float(price)

        nav = self.meta_provider.nav(meta)
        regime = str(meta.get("regime") or "NORMAL")

        # -----------------------
        # DRAW DOWN HARD HALT
        # config uses drawdown.hard_dd (see unit tests)
        # -----------------------
        dd_cfg = self.config.get("drawdown", {}) or {}
        hard_dd = float(dd_cfg.get("hard_dd", dd_cfg.get("max_dd", 999.0)))

        peak_nav = float(self._state.get("peak_nav", nav))
        # Keep peak if higher
        if nav > peak_nav:
            peak_nav = nav
            self._state["peak_nav"] = peak_nav
            self._save_state()

        drawdown = (peak_nav - nav) / peak_nav if peak_nav > 0 else 0.0
        if drawdown >= hard_dd:
            return Decision(
                allowed=False,
                qty=0,
                reason="DRAWDOWN_HALT",
                details={"nav": nav, "peak_nav": peak_nav, "drawdown": drawdown, "hard_dd": hard_dd},
                action="HALT",
            )

        candidates: list[tuple[int, str, Dict[str, Any]]] = []

        # -----------------------
        # SYMBOL CONCENTRATION
        # -----------------------
        conc = self.config.get("concentration", {}) or {}
        max_symbol_pct_nav = float(conc.get("max_symbol_pct_nav", 1.0))
        cap_dollars = nav * max_symbol_pct_nav
        current_symbol_exposure = self.meta_provider.symbol_exposure(meta, symbol, price)

        if side == "BUY":
            headroom = max(cap_dollars - current_symbol_exposure, 0.0)
            max_qty = self._floor_qty(headroom / price)
            if max_qty < requested_qty:
                candidates.append(
                    (
                        max_qty,
                        "SYMBOL_CONCENTRATION_RESIZE",
                        {
                            "symbol": symbol,
                            "nav": nav,
                            "cap_dollars": cap_dollars,
                            "current_symbol_exposure": current_symbol_exposure,
                            "requested_qty": requested_qty,
                            "price": price,
                        },
                    )
                )

        # -----------------------
        # GROSS LEVERAGE
        # leverage.gross_max_by_bucket[regime] (see unit tests)
        # -----------------------
        lev = self.config.get("leverage", {}) or {}
        gross_by_bucket = lev.get("gross_max_by_bucket", {}) if isinstance(lev.get("gross_max_by_bucket"), dict) else {}
        max_gross = float(gross_by_bucket.get(regime, gross_by_bucket.get("NORMAL", 999.0)))

        gross_cap = nav * max_gross
        current_gross = self.meta_provider.gross_exposure(meta, price)

        if side == "BUY":
            gross_headroom = max(gross_cap - current_gross, 0.0)
            max_qty = self._floor_qty(gross_headroom / price)
            if max_qty < requested_qty:
                candidates.append(
                    (
                        max_qty,
                        "GROSS_LEVERAGE_RESIZE",
                        {
                            "regime": regime,
                            "nav": nav,
                            "max_gross": max_gross,
                            "gross_cap": gross_cap,
                            "current_gross": current_gross,
                            "requested_qty": requested_qty,
                            "price": price,
                        },
                    )
                )

        # -----------------------
        # VAR LIMIT (VaR95)
        # var_es.var_95_max and meta["var_95_increment"] means:
        #   "increment in var_95 if you take this order at FULL requested size"
        # Unit test sets: var_95_increment=0.005 for qty=100
        # So per-unit increment = 0.005/100
        # -----------------------
        var_cfg = self.config.get("var_es", {}) or {}
        var_95_max = float(var_cfg.get("var_95_max", 1.0))

        rm = self.meta_provider.risk_metrics(meta)
        current_var_95 = float(rm.get("var_95", 0.0))

        inc_full = meta.get("var_95_increment", None)
        try:
            inc_full_f = float(inc_full) if inc_full is not None else 0.0
        except Exception:
            inc_full_f = 0.0

        if inc_full_f > 0.0:
            per_unit_inc = inc_full_f / max(1, requested_qty)
            headroom = var_95_max - current_var_95

            if headroom <= 0:
                candidates.append((0, "VAR_95_BLOCK", {"var_95_max": var_95_max, "current_var_95": current_var_95}))
            else:
                max_qty = self._floor_qty(headroom / per_unit_inc)
                if max_qty < requested_qty:
                    candidates.append(
                        (
                            max_qty,
                            "VAR_95_RESIZE",
                            {
                                "var_95_max": var_95_max,
                                "current_var_95": current_var_95,
                                "headroom": headroom,
                                "var_95_increment_full": inc_full_f,
                                "per_unit_inc": per_unit_inc,
                                "requested_qty": requested_qty,
                            },
                        )
                    )

        # -----------------------
        # Apply tightest (min qty)
        # -----------------------
        if candidates:
            max_qty, reason, details = min(candidates, key=lambda t: t[0])
            max_qty = int(max(0, max_qty))

            if max_qty <= 0:
                return Decision(allowed=False, qty=0, reason=reason, details=details, action="BLOCK")

            return Decision(allowed=True, qty=max_qty, reason=reason, details=details, action="RESIZE")

        return Decision(allowed=True, qty=requested_qty, reason="OK", details={"requested_qty": requested_qty}, action="ALLOW")
