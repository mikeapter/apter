"""
Market Intelligence Brief engine.

NON-NEGOTIABLE:
- Narrative must be derived from validated numeric quotes only.
- Narrative uses safe ranges (not fragile exact decimals).
- Outputs volatility label (never N/A), breadth label, regime label.

This module receives quotes (computed change_percent etc.) and returns:
- precise values (for UI chips)
- narrative text (safe)
- labels + explanations
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .market_data_provider import Quote


# ─── Result data classes ────────────────────────────────────────────────────

@dataclass(frozen=True)
class VolatilityResult:
    label: str          # Low / Moderate / Elevated / High
    value: Optional[float]  # VIX level if available; else proxy value
    method: str         # "VIX" or "SPY_RANGE_PROXY"


@dataclass(frozen=True)
class BreadthResult:
    label: str          # Broad / Moderate / Narrow
    green: int
    red: int
    total: int
    explanation: str


@dataclass(frozen=True)
class BriefResult:
    asOfUtc: str
    symbols: List[str]
    quotes: Dict[str, dict]  # serializable quote dicts
    narrative: str
    regime: str             # Risk-On / Risk-Off / Neutral
    volatility: VolatilityResult
    breadth: BreadthResult
    what_changed: List[str]
    catalysts: List[str]


# ─── Narrative helper: convert percent change to stable wording bucket ──────

def _range_phrase(pct: float) -> str:
    """Convert percent change magnitude into a stable wording bucket."""
    a = abs(pct)
    if a < 0.25:
        return "little changed"
    if a < 0.75:
        return "modestly"
    if a < 1.5:
        return "notably"
    if a < 3.0:
        return "sharply"
    return "very sharply"


def _percent_bucket(pct: float) -> str:
    """
    Provide a safe range text for a percent change.
    Examples:
      0.12 -> "roughly flat"
      -0.63 -> "down about 0.5-1%"
      2.48 -> "up about 2-3%"
      -3.5 -> "down more than 3%"
    """
    a = abs(pct)
    sign = "up" if pct > 0 else "down"

    if a < 0.25:
        return "roughly flat"
    if a < 0.5:
        return f"{sign} less than 0.5%"
    if a < 1.0:
        return f"{sign} about 0.5-1%"
    if a < 1.5:
        return f"{sign} about 1-1.5%"
    if a < 2.0:
        return f"{sign} about 1.5-2%"
    if a < 3.0:
        return f"{sign} about {int(a)}-{int(a) + 1}%"
    return f"{sign} more than 3%"


def _direction_word(pct: float) -> str:
    """Simple direction word: 'higher', 'lower', or 'flat'."""
    if pct > 0.15:
        return "higher"
    if pct < -0.15:
        return "lower"
    return "flat"


# ─── Volatility classification ─────────────────────────────────────────────

def _classify_volatility_from_vix(vix_quote: Optional[Quote]) -> VolatilityResult:
    """
    If we have a VIX quote, classify volatility from it.
    VIX thresholds (industry-standard):
      < 15  -> Low
      15-20 -> Moderate
      20-30 -> Elevated
      >= 30 -> High
    """
    if vix_quote is None or not math.isfinite(vix_quote.price):
        return VolatilityResult(label="Moderate", value=None, method="DEFAULT")

    v = vix_quote.price
    if v < 15:
        label = "Low"
    elif v < 20:
        label = "Moderate"
    elif v < 30:
        label = "Elevated"
    else:
        label = "High"

    return VolatilityResult(label=label, value=round(v, 2), method="VIX")


def _classify_volatility_from_range(spy_quote: Optional[Quote]) -> VolatilityResult:
    """
    Proxy volatility from SPY intraday range when VIX is unavailable.
    range_pct = (day_high - day_low) / previous_close * 100
    Thresholds:
      < 0.5%  -> Low
      0.5-1%  -> Moderate
      1-2%    -> Elevated
      >= 2%   -> High
    """
    if spy_quote is None:
        return VolatilityResult(label="Moderate", value=None, method="DEFAULT")

    high = spy_quote.day_high
    low = spy_quote.day_low
    prev = spy_quote.previous_close

    if high is None or low is None or prev <= 0:
        # Fall back to absolute change_percent as proxy
        pct = abs(spy_quote.change_percent)
        if pct < 0.3:
            label = "Low"
        elif pct < 0.8:
            label = "Moderate"
        elif pct < 1.5:
            label = "Elevated"
        else:
            label = "High"
        return VolatilityResult(label=label, value=round(pct, 2), method="SPY_CHANGE_PROXY")

    range_pct = ((high - low) / prev) * 100.0
    if range_pct < 0.5:
        label = "Low"
    elif range_pct < 1.0:
        label = "Moderate"
    elif range_pct < 2.0:
        label = "Elevated"
    else:
        label = "High"

    return VolatilityResult(label=label, value=round(range_pct, 2), method="SPY_RANGE_PROXY")


# ─── Breadth classification ────────────────────────────────────────────────

def _classify_breadth(quotes: Dict[str, Quote]) -> BreadthResult:
    """
    Breadth = how many symbols are green vs red.
    Thresholds (fraction green of total):
      >= 0.65 -> Broad
      0.35-0.65 -> Moderate
      < 0.35 -> Narrow
    """
    green = 0
    red = 0
    for q in quotes.values():
        if q.change_percent > 0.05:
            green += 1
        elif q.change_percent < -0.05:
            red += 1
        # Flat symbols counted as neither

    total = len(quotes)
    if total == 0:
        return BreadthResult(
            label="Moderate", green=0, red=0, total=0,
            explanation="No quotes available for breadth analysis.",
        )

    frac_green = green / total
    if frac_green >= 0.65:
        label = "Broad"
        explanation = f"{green} of {total} symbols are positive — broad participation."
    elif frac_green >= 0.35:
        label = "Moderate"
        explanation = f"{green} of {total} symbols are positive — mixed participation."
    else:
        label = "Narrow"
        explanation = f"Only {green} of {total} symbols are positive — narrow breadth."

    return BreadthResult(
        label=label, green=green, red=red, total=total, explanation=explanation,
    )


# ─── Regime classification ─────────────────────────────────────────────────

def _classify_regime(
    breadth: BreadthResult,
    volatility: VolatilityResult,
    spy_quote: Optional[Quote],
) -> str:
    """
    Simple regime label: Risk-On / Risk-Off / Neutral
    Logic:
    - Risk-On: breadth is Broad AND volatility is Low or Moderate AND SPY is up
    - Risk-Off: breadth is Narrow OR volatility is High OR SPY down > 1%
    - Otherwise: Neutral
    """
    spy_up = spy_quote is not None and spy_quote.change_percent > 0.15
    spy_down_hard = spy_quote is not None and spy_quote.change_percent < -1.0

    if spy_down_hard or volatility.label == "High" or breadth.label == "Narrow":
        return "Risk-Off"
    if breadth.label == "Broad" and volatility.label in ("Low", "Moderate") and spy_up:
        return "Risk-On"
    return "Neutral"


# ─── Narrative builder ──────────────────────────────────────────────────────

# Well-known index/ETF display names
_DISPLAY_NAMES: Dict[str, str] = {
    "SPY": "the S&P 500 (SPY)",
    "QQQ": "the Nasdaq 100 (QQQ)",
    "DIA": "the Dow (DIA)",
    "IWM": "small caps (IWM)",
    "^VIX": "the VIX",
    "TLT": "long-term Treasuries (TLT)",
    "GLD": "gold (GLD)",
}


def _build_narrative(
    quotes: Dict[str, Quote],
    volatility: VolatilityResult,
    breadth: BreadthResult,
    regime: str,
) -> str:
    """
    Build a short, deterministic narrative paragraph from validated numeric inputs only.
    No hallucinated numbers. Uses range phrases and direction words.
    """
    parts: List[str] = []

    # Lead with major indices
    spy = quotes.get("SPY")
    qqq = quotes.get("QQQ")

    if spy:
        parts.append(
            f"The S&P 500 (SPY) is {_percent_bucket(spy.change_percent)} today, "
            f"trading {_range_phrase(spy.change_percent)} {_direction_word(spy.change_percent)}"
            f" from yesterday's close."
        )
    if qqq:
        parts.append(
            f"The Nasdaq 100 (QQQ) is {_percent_bucket(qqq.change_percent)}."
        )

    # Volatility sentence
    if volatility.method == "VIX" and volatility.value is not None:
        parts.append(
            f"Volatility is {volatility.label.lower()} "
            f"with the VIX near {int(volatility.value)}."
        )
    else:
        parts.append(f"Volatility reads as {volatility.label.lower()}.")

    # Breadth sentence
    parts.append(breadth.explanation)

    # Regime sentence
    regime_descriptions = {
        "Risk-On": "Market conditions favor risk-on positioning.",
        "Risk-Off": "Market conditions suggest a risk-off posture — caution is warranted.",
        "Neutral": "Market conditions are mixed — no strong directional bias.",
    }
    parts.append(regime_descriptions.get(regime, "Market conditions are mixed."))

    # Notable movers (biggest absolute moves)
    sorted_by_move = sorted(
        quotes.values(),
        key=lambda q: abs(q.change_percent),
        reverse=True,
    )
    notable = [
        q for q in sorted_by_move
        if abs(q.change_percent) >= 1.5 and q.symbol not in ("SPY", "QQQ", "DIA", "^VIX")
    ][:3]

    if notable:
        mover_strs = []
        for q in notable:
            name = _DISPLAY_NAMES.get(q.symbol, q.symbol)
            mover_strs.append(f"{name} ({_percent_bucket(q.change_percent)})")
        parts.append("Notable movers: " + "; ".join(mover_strs) + ".")

    return " ".join(parts)


# ─── What-changed bullets ──────────────────────────────────────────────────

def _build_what_changed(quotes: Dict[str, Quote]) -> List[str]:
    """Generate bullet-point summaries of what moved significantly."""
    bullets: List[str] = []

    for sym in ("SPY", "QQQ", "DIA", "IWM"):
        q = quotes.get(sym)
        if q and abs(q.change_percent) >= 0.3:
            name = _DISPLAY_NAMES.get(sym, sym)
            bullets.append(f"{name} moved {_range_phrase(q.change_percent)} ({_percent_bucket(q.change_percent)}).")

    # Add any stock with > 2% move
    for q in sorted(quotes.values(), key=lambda x: abs(x.change_percent), reverse=True):
        if q.symbol in ("SPY", "QQQ", "DIA", "IWM", "^VIX"):
            continue
        if abs(q.change_percent) >= 2.0 and len(bullets) < 8:
            bullets.append(f"{q.symbol} is {_percent_bucket(q.change_percent)}.")

    if not bullets:
        bullets.append("No major moves across tracked symbols.")

    return bullets


# ─── Catalysts (static context-aware bullets) ──────────────────────────────

def _build_catalysts(
    volatility: VolatilityResult,
    breadth: BreadthResult,
    regime: str,
) -> List[str]:
    """
    Generate context-aware catalyst observations.
    These are NOT predictions — they describe observable conditions.
    """
    catalysts: List[str] = []

    if volatility.label in ("Elevated", "High"):
        catalysts.append(
            "Elevated volatility may reflect upcoming macro events or earnings catalysts."
        )

    if breadth.label == "Narrow":
        catalysts.append(
            "Narrow breadth suggests gains are concentrated in few names — "
            "rotation risk is present."
        )
    elif breadth.label == "Broad":
        catalysts.append(
            "Broad participation across sectors supports the current move."
        )

    if regime == "Risk-Off":
        catalysts.append(
            "Risk-off positioning is dominant — "
            "defensive sectors and safe havens may see relative strength."
        )

    if not catalysts:
        catalysts.append(
            "No unusual catalysts observed in current session data."
        )

    return catalysts


# ─── Main brief builder ────────────────────────────────────────────────────

def build_brief(quotes: Dict[str, Quote]) -> BriefResult:
    """
    Build a complete Market Intelligence Brief from validated quotes.

    Inputs: Dict of symbol -> Quote (already validated by market_data_provider).
    Outputs: BriefResult with narrative, labels, and structured data.
    """
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Volatility: prefer VIX quote if available, else use SPY range proxy
    vix_quote = quotes.get("^VIX")
    spy_quote = quotes.get("SPY")

    if vix_quote is not None:
        volatility = _classify_volatility_from_vix(vix_quote)
    else:
        volatility = _classify_volatility_from_range(spy_quote)

    # Breadth: across all non-VIX quotes
    breadth_quotes = {k: v for k, v in quotes.items() if k != "^VIX"}
    breadth = _classify_breadth(breadth_quotes)

    # Regime
    regime = _classify_regime(breadth, volatility, spy_quote)

    # Narrative
    narrative = _build_narrative(quotes, volatility, breadth, regime)

    # What changed
    what_changed = _build_what_changed(quotes)

    # Catalysts
    catalysts = _build_catalysts(volatility, breadth, regime)

    # Serialize quotes to dicts for JSON response
    quotes_dict: Dict[str, dict] = {}
    for sym, q in quotes.items():
        quotes_dict[sym] = {
            "symbol": q.symbol,
            "price": round(q.price, 2),
            "previousClose": round(q.previous_close, 2),
            "change": round(q.change, 2),
            "changePercent": round(q.change_percent, 2),
            "dayHigh": round(q.day_high, 2) if q.day_high is not None else None,
            "dayLow": round(q.day_low, 2) if q.day_low is not None else None,
            "timestampUtc": q.timestamp_utc,
        }

    return BriefResult(
        asOfUtc=now_iso,
        symbols=list(quotes.keys()),
        quotes=quotes_dict,
        narrative=narrative,
        regime=regime,
        volatility=volatility,
        breadth=breadth,
        what_changed=what_changed,
        catalysts=catalysts,
    )
