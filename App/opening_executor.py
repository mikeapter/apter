from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from Core.position_sizing import PositionSizer, SizeInputs
from Core.stops import StopModule, StopInputs

# STEP 13 (Alpha Stack)
try:
    from Core.alpha_stack import AlphaStack  # type: ignore
    from Core.signals.base import AlphaContext  # type: ignore
except Exception:  # pragma: no cover
    AlphaStack = None  # type: ignore
    AlphaContext = None  # type: ignore


LOG = logging.getLogger("opening_executor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

print(">>> opening_executor.py LOADED (STEP11 STOPS + STEP13 ALPHA + RICH FEATURES + FADE CONFLICT GUARD + ONE_SHOT SAFE) <<<")


def _now() -> datetime:
    return datetime.utcnow()


def _spread_pct(bid: float, ask: float) -> float:
    mid = (bid + ask) / 2.0
    if mid <= 0:
        return 1.0
    return (ask - bid) / mid


def _dir_from_side(side: str) -> int:
    s = (side or "").strip().lower()
    if s == "buy":
        return 1
    if s == "sell":
        return -1
    return 0


class BlockTrade(RuntimeError):
    """Raised when we want to block a trade cleanly (not crash the whole run)."""


@dataclass(frozen=True)
class SymbolPlan:
    symbol: str
    state: str  # FADE / MOMENTUM / NO_TRADE
    side: Optional[str]  # "buy"/"sell"
    ref_price: float
    gap_pct: float
    trigger_price: float
    stop_price: float
    max_qty: int
    kill_after_seconds: int
    max_slippage_bps: float


class OpeningExecutor:
    STRATEGY_ID = "opening_playbook"

    def __init__(
        self,
        *,
        data: Any,
        order_exec: Any,
        repo_root: Path,
        config_path: Path,
    ) -> None:
        self.data = data
        self.order_exec = order_exec
        self.repo_root = Path(repo_root)
        self.config_path = Path(config_path)

        self._cfg: Dict[str, Any] = {}
        self.reload()

        # ---- STEP 10 sizing ----
        sizing_cfg = self._resolve_config_file(["position_sizing.yaml"])
        self.sizer = PositionSizer(sizing_cfg)

        # ---- STEP 11 stops ----
        stops_cfg = self._resolve_config_file(["stops.yaml"])
        self.stop_mod = StopModule(stops_cfg)

        # ---- STEP 13 alpha stack ----
        self.alpha_stack = self._init_alpha_stack()

    # ----------------------------
    # Config file resolver (config vs Config)
    # ----------------------------
    def _resolve_config_file(self, candidates: List[str]) -> Path:
        """
        Your project sometimes uses config/ and sometimes Config/.
        We search both to find the file that exists.
        """
        roots = [
            self.repo_root / "config",
            self.repo_root / "Config",
        ]
        for r in roots:
            for name in candidates:
                p = r / name
                if p.exists():
                    return p
        # last resort: fall back to config_path directory
        fallback = self.config_path.parent / candidates[0]
        return fallback

    # ----------------------------
    # AlphaStack init (robust for config_path required)
    # ----------------------------
    def _find_alpha_stack_cfg(self) -> Path:
        candidates = [
            "alpha_stack.yaml",
            "alpha_stack.yml",
            "strategy_alpha_stack.yaml",
            "strategy_alpha_stack.yml",
            "alpha.yaml",
            "alpha.yml",
        ]
        for name in candidates:
            p = self._resolve_config_file([name])
            if p.exists():
                return p
        return self.config_path  # fallback

    def _init_alpha_stack(self) -> Any:
        if AlphaStack is None:
            return None

        cfg_path = self._find_alpha_stack_cfg()

        try:
            return AlphaStack(cfg_path)
        except TypeError:
            try:
                return AlphaStack(config_path=cfg_path)
            except TypeError:
                return AlphaStack()

    # ----------------------------
    # Reload opening config
    # ----------------------------
    def reload(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Opening playbook config not found: {self.config_path}")
        with self.config_path.open("r", encoding="utf-8") as f:
            self._cfg = yaml.safe_load(f) or {}

        acct = self._cfg.get("account", {}) or {}
        self.equity_usd = float(acct.get("equity_usd", 0.0))

        exec_cfg = self._cfg.get("execution", {}) or {}
        self.tick_ms = int(exec_cfg.get("tick_ms", 250))
        self.opening_range_seconds = int(exec_cfg.get("opening_range_seconds", 120))
        self.exec_max_spread_pct = float(exec_cfg.get("max_spread_pct", 0.0))

        rce = self._cfg.get("regime", {}) or {}
        self.regime_label = str(rce.get("label", "UNKNOWN")).upper()
        self.regime_confidence = float(rce.get("confidence", 0.0))

        alpha_cfg = self._cfg.get("alpha", {}) or {}
        guard = alpha_cfg.get("fade_conflict_guard", {}) or {}
        self.fade_conflict_enabled = bool(guard.get("enabled", True))
        self.fade_conflict_override_score = float(guard.get("override_score", 1.0))
        self.fade_conflict_override_modules = list(guard.get("override_modules", []) or [])

    # ----------------------------
    # Optional call helper
    # ----------------------------
    def _call_optional(self, method_name: str, /, *args: Any, **kwargs: Any) -> Any:
        fn = getattr(self.data, method_name, None)
        if not callable(fn):
            return None
        try:
            return fn(*args, **kwargs)
        except TypeError:
            try:
                return fn(*args)
            except Exception:
                return None
        except Exception:
            return None

    def _get_bid_ask(self, symbol: str) -> Optional[Tuple[float, float]]:
        ba = self._call_optional("get_bid_ask", symbol)
        if ba is None:
            return None
        try:
            bid, ask = ba
            return float(bid), float(ask)
        except Exception:
            return None

    # ----------------------------
    # Universe filter
    # ----------------------------
    def build_tradable_list(self) -> List[str]:
        uni = self._cfg.get("universe", {}) or {}
        symbols = list(uni.get("symbols", []) or [])
        if not symbols:
            return []

        flt = uni.get("filters", {}) or {}
        min_gap_pct = float(flt.get("min_gap_pct", 0.02))
        min_pm_vol = int(flt.get("min_premarket_volume", 0))
        require_catalyst = bool(flt.get("require_real_catalyst", True))

        out: List[str] = []
        for sym in symbols:
            prev_close = float(self.data.get_prev_close(sym))
            pm_last = float(self.data.get_premarket_last(sym))
            pm_vol = int(self.data.get_premarket_volume(sym))
            gap = (pm_last - prev_close) / prev_close if prev_close > 0 else 0.0

            if abs(gap) < min_gap_pct:
                continue
            if pm_vol < min_pm_vol:
                continue
            if require_catalyst:
                has_cat = bool(self._call_optional("has_real_catalyst", sym))
                if not has_cat:
                    continue

            out.append(sym)

        return out

    # ----------------------------
    # Plan logic
    # ----------------------------
    def _plan_side(self, gap_pct: float) -> Optional[str]:
        if gap_pct > 0:
            return "sell"
        if gap_pct < 0:
            return "buy"
        return None

    def _make_plan(self, symbol: str) -> SymbolPlan:
        params = self._cfg.get("plan", {}) or {}

        prev_close = float(self.data.get_prev_close(symbol))
        pm_last = float(self.data.get_premarket_last(symbol))
        gap_pct = (pm_last - prev_close) / prev_close if prev_close > 0 else 0.0

        state = str(params.get("state", "FADE")).upper()
        side = self._plan_side(gap_pct)

        ref_price = float(pm_last)
        trigger_bps = float(params.get("trigger_bps", 10.0))

        if side == "sell":
            trigger_price = ref_price * (1.0 - trigger_bps / 10000.0)
        else:
            trigger_price = ref_price * (1.0 + trigger_bps / 10000.0)

        stop_price = 0.0
        max_qty = int(params.get("max_qty", 10))
        kill_after_seconds = int(params.get("kill_after_seconds", 120))
        max_slippage_bps = float(params.get("max_slippage_bps", 10.0))

        return SymbolPlan(
            symbol=symbol,
            state=state,
            side=side,
            ref_price=ref_price,
            gap_pct=gap_pct,
            trigger_price=float(trigger_price),
            stop_price=float(stop_price),
            max_qty=max_qty,
            kill_after_seconds=kill_after_seconds,
            max_slippage_bps=max_slippage_bps,
        )

    def build_plan(self, symbols: List[str]) -> Dict[str, SymbolPlan]:
        plans: Dict[str, SymbolPlan] = {}
        for sym in symbols:
            p = self._make_plan(sym)
            plans[sym] = p
            LOG.info(
                "PLAN %s | %s | side=%s | ref=%.4f | gap_pct=%.4f | trig=%.4f",
                p.symbol,
                p.state,
                p.side,
                p.ref_price,
                p.gap_pct,
                p.trigger_price,
            )
        return plans

    # ----------------------------
    # Alpha context + decision
    # ----------------------------
    def _make_alpha_context(self, payload: Dict[str, Any]) -> Any:
        if AlphaContext is None:
            return payload
        try:
            sig = inspect.signature(AlphaContext)
            kwargs: Dict[str, Any] = {}
            for name in sig.parameters.keys():
                if name in payload:
                    kwargs[name] = payload[name]
            return AlphaContext(**kwargs)
        except Exception:
            try:
                return AlphaContext(**payload)
            except Exception:
                return payload

    def _build_alpha_context(
        self,
        *,
        plan: SymbolPlan,
        last_px: float,
        bid: Optional[float],
        ask: Optional[float],
        order_size: float,
    ) -> Any:
        spread_pct = None
        spread_bps = None
        if bid is not None and ask is not None:
            sp = _spread_pct(float(bid), float(ask))
            spread_pct = sp
            spread_bps = sp * 10000.0

        planned_dir = _dir_from_side(plan.side or "")

        fill_prob = self._call_optional("get_fill_probability", plan.symbol, plan.side, order_size)
        exp_fill = self._call_optional("get_expected_fill_time_s", plan.symbol, plan.side, order_size)

        # Step 2 demo hook (trend direction feed)
        trend_dir = self._call_optional("get_trend_direction", plan.symbol)
        persistence_score = self._call_optional("get_persistence_score", plan.symbol)

        ctx_payload = {
            "symbol": plan.symbol,
            "ts": _now(),
            "features": {
                "state": plan.state,
                "planned_side": plan.side,
                "planned_dir": planned_dir,
                "gap_pct": float(plan.gap_pct),
                "ref_price": float(plan.ref_price),
                "trigger_price": float(plan.trigger_price),
                "price": float(last_px),
                "bid": float(bid) if bid is not None else None,
                "ask": float(ask) if ask is not None else None,
                "spread_pct": float(spread_pct) if spread_pct is not None else None,
                "spread_bps": float(spread_bps) if spread_bps is not None else None,
                "order_size": float(order_size),
                "regime": self.regime_label,
                "regime_confidence": float(self.regime_confidence),
                "fill_probability": float(fill_prob) if fill_prob is not None else None,
                "expected_fill_time_s": float(exp_fill) if exp_fill is not None else None,
                "trend_direction": int(trend_dir) if trend_dir is not None else None,
                "persistence_score": float(persistence_score) if persistence_score is not None else None,
            },
        }
        return self._make_alpha_context(ctx_payload)

    def _alpha_decide(self, ctx: Any) -> Any:
        if self.alpha_stack is None:
            return None

        for method in ("evaluate", "decide", "run", "__call__"):
            fn = getattr(self.alpha_stack, method, None)
            if callable(fn):
                return fn(ctx)
        return None

    def _decision_to_dict(self, decision: Any) -> Dict[str, Any]:
        if decision is None:
            return {
                "allowed": True,
                "direction": 0,
                "score": 0.0,
                "confidence": 0.0,
                "urgency": "LOW",
                "reason": "no_alpha",
                "modules": {},
                "execution_hints": {},
            }

        if isinstance(decision, dict):
            d = dict(decision)
        else:
            d = {}
            for k in ("allowed", "direction", "score", "confidence", "urgency", "reason", "modules", "execution_hints"):
                if hasattr(decision, k):
                    d[k] = getattr(decision, k)

        d.setdefault("allowed", True)
        d.setdefault("direction", 0)
        d.setdefault("score", 0.0)
        d.setdefault("confidence", 0.0)
        d.setdefault("urgency", "LOW")
        d.setdefault("reason", "ok")
        d.setdefault("modules", {})
        d.setdefault("execution_hints", {})
        return d

    # ----------------------------
    # Exec checks
    # ----------------------------
    def _exec_spread_ok(self, symbol: str) -> bool:
        if self.exec_max_spread_pct <= 0:
            return True
        ba = self._get_bid_ask(symbol)
        if ba is None:
            return True
        bid, ask = ba
        sp = _spread_pct(bid, ask)
        return sp <= self.exec_max_spread_pct

    def _trigger_hit(self, plan: SymbolPlan, last_px: float) -> bool:
        if plan.side == "buy":
            return last_px >= plan.trigger_price
        if plan.side == "sell":
            return last_px <= plan.trigger_price
        return False

    def _submit_order(self, *, symbol: str, side: str, qty: int, meta: Dict[str, Any]) -> Any:
        fn = getattr(self.order_exec, "place_order", None)
        if not callable(fn):
            raise RuntimeError("order_exec.place_order not found")
        return fn(strategy_id=self.STRATEGY_ID, symbol=symbol, side=side, qty=int(qty), type="market", meta=meta)

    # ----------------------------
    # FADE conflict guard
    # ----------------------------
    def _fade_conflict_check(self, *, plan: SymbolPlan, alpha: Dict[str, Any]) -> Optional[str]:
        if not self.fade_conflict_enabled:
            return None
        if str(plan.state).upper() != "FADE":
            return None

        planned_dir = _dir_from_side(plan.side or "")
        if planned_dir == 0:
            return None

        modules = alpha.get("modules", {}) or {}
        tp = modules.get("trend_persistence")
        if not isinstance(tp, dict):
            return None

        tp_state = (tp.get("outputs", {}) or {}).get("state")
        tp_dir = tp.get("direction", 0)
        tp_active = bool(tp.get("active", False))

        if not tp_active or str(tp_state).upper() != "STRONG":
            return None

        try:
            tp_dir_i = int(tp_dir)
        except Exception:
            tp_dir_i = 0

        if tp_dir_i == 0 or tp_dir_i == planned_dir:
            return None

        override_score = 0.0
        overrides: List[str] = []

        for name, mod in modules.items():
            if name == "trend_persistence":
                continue
            if not isinstance(mod, dict):
                continue
            if not bool(mod.get("active", False)):
                continue
            if self.fade_conflict_override_modules and name not in self.fade_conflict_override_modules:
                continue
            try:
                mdir = int(mod.get("direction", 0))
            except Exception:
                mdir = 0
            if mdir != planned_dir:
                continue
            try:
                mscore = float(mod.get("score", 0.0))
            except Exception:
                mscore = 0.0

            override_score += mscore
            overrides.append(name)

        if override_score >= self.fade_conflict_override_score:
            return None

        return (
            f"FADE_CONFLICT_BLOCK: trend_persistence=STRONG trend_dir={tp_dir_i} "
            f"conflicts with planned_dir={planned_dir}. override_score={override_score:.2f} overrides={overrides}"
        )

    # ----------------------------
    # Entry placement
    # ----------------------------
    def _place_entry(self, plan: SymbolPlan, last_px: float) -> Dict[str, Any]:
        if self.equity_usd <= 0:
            raise BlockTrade("Set account.equity_usd > 0 in opening_playbook.yaml")

        sizing_strategy_id = f"OPENING_{plan.state}".upper()
        ba = self._get_bid_ask(plan.symbol)
        bid, ask = (ba if ba else (None, None))

        alpha_dict: Dict[str, Any] = {}
        exec_hints: Dict[str, Any] = {}

        if self.alpha_stack is not None:
            ctx = self._build_alpha_context(
                plan=plan,
                last_px=float(last_px),
                bid=bid,
                ask=ask,
                order_size=float(plan.max_qty),
            )
            decision = self._alpha_decide(ctx)
            alpha_dict = self._decision_to_dict(decision)
            exec_hints = alpha_dict.get("execution_hints", {}) or {}

            reason = self._fade_conflict_check(plan=plan, alpha=alpha_dict)
            if reason is not None:
                raise BlockTrade(reason)

            if not bool(alpha_dict.get("allowed", True)):
                raise BlockTrade(f"ALPHA_BLOCK: {alpha_dict.get('reason', 'blocked')}")

        stop_res = self.stop_mod.compute(
            StopInputs(
                symbol=plan.symbol,
                side=plan.side or "BUY",
                entry_price=float(last_px),
                regime=self.regime_label,
                strategy_id=sizing_strategy_id,
                confidence=self.regime_confidence,
                bid=bid,
                ask=ask,
                equity_usd=self.equity_usd,
                qty=None,
            )
        )
        if stop_res.blocked:
            raise BlockTrade(f"STOPS_BLOCK: {stop_res.reason}")

        stop_price = float(stop_res.stop_price)
        stop_distance_usd = float(stop_res.stop_distance_usd)

        size = self.sizer.size(
            SizeInputs(
                equity_usd=float(self.equity_usd),
                price=float(last_px),
                stop_distance_usd=float(stop_distance_usd),
                regime=str(self.regime_label),
                strategy_id=str(sizing_strategy_id),
                confidence=self.regime_confidence,
            )
        )
        if size.blocked:
            raise BlockTrade(f"SIZING_BLOCK: {size.reason}")

        qty = int(min(int(size.qty), int(plan.max_qty)))
        if qty <= 0:
            raise BlockTrade("qty computed as 0")

        meta: Dict[str, Any] = {
            "strategy": self.STRATEGY_ID,
            "state": plan.state,
            "gap_pct": float(plan.gap_pct),
            "ref_price": float(plan.ref_price),
            "trigger_price": float(plan.trigger_price),
            "stop_price": float(stop_price),
            "stop_distance_usd": float(stop_distance_usd),
            "alpha": alpha_dict,
            "execution_hints": exec_hints,
        }

        self._submit_order(symbol=plan.symbol, side=plan.side or "buy", qty=qty, meta=meta)
        return meta

    # ----------------------------
    # One-shot runner (safe)
    # ----------------------------
    def run_one_shot(self) -> Dict[str, Any]:
        """
        STEP 21 CHANGE:
          - Returns {"fired": ..., "blocked": ...} so the caller (run_opening.py)
            can log BLOCKED decisions into trades.jsonl.
        """
        tradable = self.build_tradable_list()
        plans = self.build_plan(tradable)

        fired: Dict[str, str] = {}     # symbol -> ISO timestamp
        blocked: Dict[str, str] = {}   # symbol -> reason string

        for sym, plan in plans.items():
            if plan.state == "NO_TRADE" or not plan.side:
                continue

            last_px = float(self.data.get_last_trade(sym))
            hit = self._trigger_hit(plan, last_px)

            print(
                f"[CHECK] {sym} state={plan.state} side={plan.side} "
                f"last={last_px:.4f} trig={plan.trigger_price:.4f} hit={hit}"
            )

            if not hit:
                continue
            if not self._exec_spread_ok(sym):
                blocked[sym] = "SPREAD_SKIP"
                continue

            try:
                meta = self._place_entry(plan, last_px)
                print(f"[FIRE] {sym} meta={meta}")
                fired[sym] = _now().isoformat()
            except BlockTrade as e:
                reason = str(e)
                print(f"[BLOCK] {sym} reason={reason}")
                blocked[sym] = reason
            except Exception as e:
                reason = f"ENTRY_FAIL: {e}"
                print(f"[BLOCK] {sym} reason={reason}")
                blocked[sym] = reason

        print(f"[ONE_SHOT_DONE] fired={list(fired.keys())}")
        if blocked:
            print(f"[ONE_SHOT_BLOCKED] blocked={blocked}")

        # ✅ STEP 21: return structured result
        return {"fired": fired, "blocked": blocked}
