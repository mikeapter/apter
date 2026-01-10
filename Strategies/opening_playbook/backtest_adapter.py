from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import csv

from Core.promotion.backtest_engine import Bar

# =========================================================
# REQUIRED by promotion_suite:
#   load_bars() -> List[Bar]
#   fit(train_bars) -> params
#   signal(bars, params) -> List[int] targets (-1/0/+1)
# =========================================================

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]  # BotTrader/

def _parse_ts(raw: str) -> datetime:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("blank ts")
    raw = raw.replace(" ", "T")
    return datetime.fromisoformat(raw)

def load_bars() -> List[Bar]:
    """
    Loads daily SPY bars from: BotTrader/Data/SPY_daily.csv
    Expected headers (any of these variants):
      ts or Date
      open/Open, high/High, low/Low, close/Close, volume/Volume
    Skips invalid rows safely (e.g., the ',SPY,SPY,...' line you saw).
    """
    csv_path = _repo_root() / "Data" / "SPY_daily.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing data file: {csv_path}")

    bars: List[Bar] = []
    bad = 0

    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                ts_raw = row.get("ts") or row.get("Date") or row.get("date") or ""
                ts = _parse_ts(ts_raw)

                o = float((row.get("open") or row.get("Open") or "").strip())
                h = float((row.get("high") or row.get("High") or "").strip())
                l = float((row.get("low") or row.get("Low") or "").strip())
                c = float((row.get("close") or row.get("Close") or "").strip())
                v_raw = (row.get("volume") or row.get("Volume") or "0").strip()
                v = float(v_raw) if v_raw else 0.0

                if c <= 0:
                    bad += 1
                    continue

                bars.append(Bar(ts=ts, open=o, high=h, low=l, close=c, volume=v))
            except Exception:
                bad += 1
                continue

    bars.sort(key=lambda b: b.ts)

    if len(bars) < 300:
        raise ValueError(f"Too few valid rows loaded. good={len(bars)} bad={bad}")

    print(f"[adapter] Loaded {len(bars)} bars from {csv_path} (skipped {bad} bad rows)")
    return bars

# ---------------------------------------------------------
# Option A (strict IPS gate): reduce overfitting in fit()
# ---------------------------------------------------------
def fit(train_bars: List[Bar]) -> Dict[str, Any]:
    """
    Strict gate (no threshold lowering).
    Reduce in-sample inflation by:
      - smaller candidate set
      - stability preference (penalize short lookbacks)
      - require meaningful improvement to switch params
    """
    closes = [b.close for b in train_bars]
    if len(closes) < 260:
        return {"ma_lookback": 150}

    candidates = [100, 150, 200]  # tighter than before (less curve fit)

    def score_for_lb(lb: int) -> float:
        score = 0.0
        for i in range(lb, len(closes)):
            ma = sum(closes[i - lb:i]) / lb
            score += (closes[i] - ma)

        # stability penalty: prefer longer LBs
        penalty = {100: 0.10, 150: 0.05, 200: 0.00}.get(lb, 0.05)
        return score - (abs(score) * penalty)

    best_lb = 150
    best_score = score_for_lb(best_lb)

    min_improve = 0.08  # require 8% improvement to switch (stricter)

    for lb in candidates:
        s = score_for_lb(lb)
        if best_score == 0:
            if s > best_score:
                best_lb, best_score = lb, s
        else:
            improvement = (s - best_score) / abs(best_score)
            if improvement > min_improve:
                best_lb, best_score = lb, s

    return {"ma_lookback": best_lb}

def signal(bars: List[Bar], params: Dict[str, Any]) -> List[int]:
    """
    Toy signal (placeholder): MA trend filter
    +1 if close > MA
    -1 if close < MA
     0 otherwise
    """
    lb = int(params.get("ma_lookback", 150))
    closes = [b.close for b in bars]
    targets: List[int] = [0] * len(bars)

    for i in range(len(bars)):
        if i < lb:
            targets[i] = 0
            continue
        ma = sum(closes[i - lb:i]) / lb
        if closes[i] > ma:
            targets[i] = 1
        elif closes[i] < ma:
            targets[i] = -1
        else:
            targets[i] = 0

    return targets
