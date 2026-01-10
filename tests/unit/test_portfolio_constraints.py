from __future__ import annotations

from pathlib import Path

import yaml

from Core.portfolio_constraints import MetaPortfolioProvider, PortfolioConstraintsGate


def _write_cfg(tmp_path: Path) -> Path:
    cfg = {
        "portfolio_constraints": {
            "version": 1,
            "concentration": {
                "max_symbol_pct_nav": 0.05,
                "max_sector_pct_nav": 0.20,
                "max_country_pct_nav": 0.20,
                "max_factor_pct_nav": 0.10,
                "max_asset_class_pct_nav": 0.25,
            },
            "leverage": {
                "gross_max_by_bucket": {"NORMAL": 2.0, "CRISIS": 0.5, "LIQUIDITY_VACUUM": 1.0, "EVENT": 1.0, "HIGH_VOL": 1.6},
                "net_max_abs": 1.5,
            },
            "var_es": {
                "require_inputs": False,
                "var_95_max": 0.03,
                "var_99_max": 0.05,
                "es_97_5_max": 0.05,
                "es_normal_max": 0.07,
                "eps": 1e-9,
                "default_daily_vol": 0.015,
                "corr_same_sector": 0.60,
                "corr_diff_sector": 0.30,
            },
            "drawdown": {
                "mode": "HARD",
                "hard_dd": 0.15,
                "max_dd": 0.20,
                "default_risk_mult": 1.0,
                "tiers": [
                    {"min_dd": 0.00, "max_dd": 0.05, "risk_mult": 1.0},
                    {"min_dd": 0.05, "max_dd": 0.10, "risk_mult": 0.75},
                    {"min_dd": 0.10, "max_dd": 0.15, "risk_mult": 0.50},
                    {"min_dd": 0.15, "max_dd": 0.20, "risk_mult": 0.25},
                ],
            },
            "risk_share": {"min_strategies_for_cap": 2, "strategy_risk_target": 0.30, "strategy_risk_hard_cap": 0.40, "default_daily_vol": 0.015},
        }
    }
    p = tmp_path / "portfolio_constraints.yaml"
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return p


class DummyOrder:
    def __init__(self, symbol: str, side: str, qty: int, strategy: str, meta: dict):
        self.symbol = symbol
        self.side = side
        self.qty = qty
        self.strategy = strategy
        self.meta = meta


def test_symbol_concentration_resizes(tmp_path: Path):
    cfg_path = _write_cfg(tmp_path)
    gate = PortfolioConstraintsGate.from_yaml(cfg_path, meta_provider=MetaPortfolioProvider())

    meta = {
        "portfolio": {
            "nav": 100_000,
            "equity": 100_000,
            "cash": 10_000,
            "positions": [
                {"symbol": "SPY", "qty": 40, "price": 100, "sector": "EQUITY_INDEX", "country": "US", "strategy": "CORE", "daily_vol": 0.012},
            ],
            "risk_metrics": {"var_95": 0.01, "var_99": 0.02, "es_97_5": 0.02},
        },
        "price": 100,
        "sector": "EQUITY_INDEX",
        "country": "US",
        "regime": "NORMAL",
    }
    # current SPY exposure = 4,000 (4% NAV). cap = 5,000 => headroom 1,000 => 10 shares
    o = DummyOrder("SPY", "BUY", 50, "CORE", meta)
    dec = gate.check_pre_trade(o, meta=meta, price=100)
    assert dec.allowed is True
    assert dec.action in ("RESIZE", "ALLOW")
    assert dec.adjusted_qty == 10


def test_gross_leverage_resizes(tmp_path: Path):
    cfg_path = _write_cfg(tmp_path)
    gate = PortfolioConstraintsGate.from_yaml(cfg_path, meta_provider=MetaPortfolioProvider())
    # For this test we isolate leverage (make symbol cap non-binding)
    gate.config["concentration"]["max_symbol_pct_nav"] = 1.0

    meta = {
        "portfolio": {
            "nav": 100_000,
            "equity": 100_000,
            "cash": 0,
            "positions": [
                {"symbol": "AAA", "qty": 1600, "price": 100, "sector": "OTHER", "country": "CA", "strategy": "S1", "daily_vol": 0.02},
                {"symbol": "CCC", "qty": 300, "side": "SHORT", "price": 100, "sector": "HEDGE", "country": "CA", "strategy": "S1", "daily_vol": 0.02},
            ],
            "risk_metrics": {"var_95": 0.01, "var_99": 0.02, "es_97_5": 0.02},
        },
        "price": 100,
        "sector": "FIN",
        "country": "US",
        "regime": "NORMAL",
    }
    # gross before = 190k (1.9x). max gross = 2.0x => headroom 10k => 100 shares
    o = DummyOrder("BBB", "BUY", 300, "S1", meta)
    dec = gate.check_pre_trade(o, meta=meta, price=100)
    assert dec.allowed is True
    assert dec.adjusted_qty == 100


def test_var_limit_resizes(tmp_path: Path):
    cfg_path = _write_cfg(tmp_path)
    gate = PortfolioConstraintsGate.from_yaml(cfg_path, meta_provider=MetaPortfolioProvider())

    meta = {
        "portfolio": {
            "nav": 100_000,
            "equity": 100_000,
            "cash": 0,
            "positions": [],
            "risk_metrics": {"var_95": 0.029, "var_99": 0.045, "es_97_5": 0.040},
        },
        "price": 100,
        "sector": "TECH",
        "country": "US",
        "regime": "NORMAL",
        # assume this trade adds +0.005 VaR95 at full size (qty=100)
        "var_95_increment": 0.005,
    }
    o = DummyOrder("XYZ", "BUY", 100, "S1", meta)
    dec = gate.check_pre_trade(o, meta=meta, price=100)
    assert dec.allowed is True
    # allowed headroom = 0.001 (3.0% - 2.9%) => scale 0.001/0.005 = 0.2 => qty 20
    assert dec.adjusted_qty == 20


def test_drawdown_halt_blocks_entries(tmp_path: Path):
    cfg_path = _write_cfg(tmp_path)
    gate = PortfolioConstraintsGate.from_yaml(cfg_path, meta_provider=MetaPortfolioProvider())
    # seed state peak_nav to 100k
    gate._state["peak_nav"] = 100_000
    gate._save_state()

    meta = {
        "portfolio": {
            "nav": 80_000,  # 20% drawdown
            "equity": 80_000,
            "cash": 0,
            "positions": [],
            "risk_metrics": {"var_95": 0.01, "var_99": 0.02, "es_97_5": 0.02},
        },
        "price": 100,
        "sector": "TECH",
        "country": "US",
        "regime": "NORMAL",
    }
    o = DummyOrder("XYZ", "BUY", 10, "S1", meta)
    dec = gate.check_pre_trade(o, meta=meta, price=100)
    assert dec.allowed is False
    assert dec.action in ("HALT", "BLOCK")
