from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _side_sign(side: str) -> int:
    s = str(side).upper().strip()
    return +1 if s in ("BUY", "B", "LONG") else -1


def _impl_shortfall_bps(arrival: Optional[float], fill: Optional[float], side: str) -> Optional[float]:
    if arrival is None or fill is None:
        return None
    if arrival <= 0:
        return None
    sign = _side_sign(side)
    val = (fill - arrival) / arrival * 10000.0
    return val if sign == +1 else (-val)


def _half_spread_bps(arrival: Optional[float], bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    if arrival is None or arrival <= 0:
        return None
    if bid is None or ask is None:
        return None
    spr = max(0.0, float(ask) - float(bid))
    return (spr / arrival) * 10000.0 * 0.5


@dataclass(frozen=True)
class TCAConfig:
    min_trades_for_stats: int = 20


class TCAEngine:
    """
    STEP 21 — TCA (transaction cost analysis) engine.

    Reads Data/Logs/trades.jsonl and produces:
      - per-trade metrics: IS bps, spread estimate, fees bps, total_cost_bps
      - rollups by broker/venue and strategy/regime
      - monthly report (HTML + JSON summary)
    """

    def __init__(self, *, trade_log_path: Path, cfg: Optional[TCAConfig] = None) -> None:
        self.trade_log_path = Path(trade_log_path)
        self.cfg = cfg or TCAConfig()

    def load_events(self) -> pd.DataFrame:
        if not self.trade_log_path.exists():
            return pd.DataFrame()

        rows: List[Dict[str, Any]] = []
        with self.trade_log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        df["ts"] = pd.to_numeric(df.get("ts"), errors="coerce")
        df["event_type"] = df.get("event_type", "").astype(str)
        df["symbol"] = df.get("symbol", "").astype(str).str.upper()
        df["side"] = df.get("side", "").astype(str).str.upper()
        df["strategy"] = df.get("strategy", "").astype(str).str.upper()
        df["regime"] = df.get("regime", "UNKNOWN").astype(str).str.upper()
        df["broker"] = df.get("broker", "").fillna("").astype(str)
        df["venue"] = df.get("venue", "").fillna("").astype(str)
        df["order_type"] = df.get("order_type", "").fillna("").astype(str)

        for col in ("qty", "arrival_price", "fill_price", "bid", "ask", "commission_usd", "fees_usd", "latency_ms"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def compute_trade_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        trades = df[df["event_type"].isin(["ORDER_FILLED", "ORDER_SUBMITTED"])].copy()
        if trades.empty:
            return trades

        trades["impl_shortfall_bps"] = trades.apply(
            lambda r: _impl_shortfall_bps(_safe_float(r.get("arrival_price")), _safe_float(r.get("fill_price")), r.get("side", "")),
            axis=1,
        )
        trades["half_spread_bps"] = trades.apply(
            lambda r: _half_spread_bps(_safe_float(r.get("arrival_price")), _safe_float(r.get("bid")), _safe_float(r.get("ask"))),
            axis=1,
        )
        trades["market_impact_bps"] = trades["impl_shortfall_bps"] - trades["half_spread_bps"]

        trades["notional_usd"] = (trades["qty"].fillna(0).abs() * trades["fill_price"].fillna(0)).astype(float)
        trades["fees_total_usd"] = trades["commission_usd"].fillna(0.0) + trades["fees_usd"].fillna(0.0)
        trades["fees_bps"] = trades.apply(
            lambda r: (r["fees_total_usd"] / r["notional_usd"] * 10000.0) if r["notional_usd"] > 0 else None,
            axis=1,
        )
        trades["total_cost_bps"] = trades["impl_shortfall_bps"] + trades["fees_bps"]

        trades["dt"] = pd.to_datetime(trades["ts"], unit="s", utc=True).dt.tz_convert("America/Chicago")
        trades["date"] = trades["dt"].dt.date
        trades["month"] = trades["dt"].dt.to_period("M").astype(str)
        return trades

    def aggregate(self, trade_metrics: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        if trade_metrics.empty:
            return {k: pd.DataFrame() for k in ("by_broker", "by_venue", "by_strategy", "by_broker_venue", "by_month")}

        def agg(df: pd.DataFrame, by: List[str]) -> pd.DataFrame:
            g = df.groupby(by, dropna=False)
            out = g.agg(
                trades=("symbol", "count"),
                notional_usd=("notional_usd", "sum"),
                avg_is_bps=("impl_shortfall_bps", "mean"),
                p50_is_bps=("impl_shortfall_bps", lambda x: x.quantile(0.50)),
                p90_is_bps=("impl_shortfall_bps", lambda x: x.quantile(0.90)),
                avg_fees_bps=("fees_bps", "mean"),
                avg_total_cost_bps=("total_cost_bps", "mean"),
                avg_latency_ms=("latency_ms", "mean"),
            ).reset_index()
            return out.sort_values(["avg_total_cost_bps", "p90_is_bps"], ascending=True)

        return {
            "by_broker": agg(trade_metrics, ["broker"]),
            "by_venue": agg(trade_metrics, ["venue"]),
            "by_strategy": agg(trade_metrics, ["strategy", "regime"]),
            "by_broker_venue": agg(trade_metrics, ["broker", "venue"]),
            "by_month": agg(trade_metrics, ["month", "broker", "venue"]),
        }

    def write_monthly_report(self, *, out_dir: Path, month: Optional[str] = None) -> Path:
        df = self.load_events()
        tm = self.compute_trade_metrics(df)

        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        if tm.empty:
            p = out_dir / "tca_empty.html"
            p.write_text("<h2>No trade events found for TCA.</h2>", encoding="utf-8")
            return p

        if month is None:
            now = datetime.now(timezone.utc)
            y = now.year
            m = now.month - 1
            if m == 0:
                m = 12
                y -= 1
            month = f"{y:04d}-{m:02d}"

        tm_m = tm[tm["month"] == month].copy()
        aggs = self.aggregate(tm_m)

        title = f"TCA Report — {month}"
        html = [f"<h1>{title}</h1>", f"<p>Trades in month: {len(tm_m)}</p>"]

        for k, table in aggs.items():
            html.append(f"<h2>{k}</h2>")
            if table.empty:
                html.append("<p><em>No data.</em></p>")
            else:
                html.append(table.to_html(index=False, float_format=lambda x: f"{x:,.3f}"))

        out_path = out_dir / f"tca_{month.replace('-', '_')}.html"
        out_path.write_text("\n".join(html), encoding="utf-8")

        summary_path = out_dir / f"tca_{month.replace('-', '_')}.json"
        summary = {
            "month": month,
            "trades": int(len(tm_m)),
            "by_broker_venue": aggs["by_broker_venue"].to_dict(orient="records") if not aggs["by_broker_venue"].empty else [],
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return out_path
