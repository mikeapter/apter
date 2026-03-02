"""
Portfolio analytics endpoints.

POST /api/portfolio/summary   — Compute portfolio metrics from client-side holdings
POST /api/portfolio/ai-brief  — AI-generated portfolio brief (grounded in data only)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from app.models.user import User
from app.services.market_data import fetch_quote, get_stock_name, get_stock_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


# ─── Request / Response models ────────────────────────────────────────────────


class HoldingInput(BaseModel):
    ticker: str
    shares: float = Field(gt=0)
    purchasePrice: float = Field(gt=0)


class SummaryRequest(BaseModel):
    holdings: List[HoldingInput]
    range: str = "1M"


class AIBriefRequest(BaseModel):
    holdings: List[HoldingInput]
    range: str = "1M"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_sector(ticker: str) -> str:
    """Resolve sector from the internal stock database."""
    stock_db = get_stock_db()
    entry = stock_db.get(ticker.upper())
    if entry:
        return entry.get("sector", "Other")
    return "Other"


def _compute_summary(holdings: List[HoldingInput], range_val: str) -> dict:
    """Core portfolio computation shared by summary and ai-brief."""

    if not holdings:
        return {
            "range": range_val,
            "asOf": datetime.now(timezone.utc).isoformat(),
            "totals": {
                "marketValue": 0,
                "costBasis": 0,
                "unrealizedPL": 0,
                "unrealizedPLPct": 0,
                "dayPL": 0,
                "dayPLPct": 0,
            },
            "holdings": [],
            "sectorAllocations": [],
            "contributors": {"topGainers": [], "topLosers": []},
            "concentration": {
                "topHoldingWeightPct": 0,
                "top3WeightPct": 0,
                "maxSectorWeightPct": 0,
                "flags": [],
            },
        }

    enriched: list[dict] = []
    total_market_value = 0.0
    total_cost_basis = 0.0
    total_day_pl = 0.0

    for h in holdings:
        ticker = h.ticker.strip().upper()
        quote = fetch_quote(ticker)
        price = quote.get("price", 0)
        change = quote.get("change", 0)

        market_value = h.shares * price
        cost_basis = h.shares * h.purchasePrice
        unrealized_pl = market_value - cost_basis
        unrealized_pl_pct = (
            (unrealized_pl / cost_basis * 100) if cost_basis > 0 else 0
        )
        day_pl = h.shares * change

        sector = _get_sector(ticker)
        name = get_stock_name(ticker)

        enriched.append(
            {
                "ticker": ticker,
                "name": name,
                "sector": sector,
                "shares": h.shares,
                "avgCost": round(h.purchasePrice, 2),
                "price": round(price, 2),
                "marketValue": round(market_value, 2),
                "costBasis": round(cost_basis, 2),
                "unrealizedPL": round(unrealized_pl, 2),
                "unrealizedPLPct": round(unrealized_pl_pct, 2),
                "dayPL": round(day_pl, 2),
                "weightPct": 0.0,
            }
        )

        total_market_value += market_value
        total_cost_basis += cost_basis
        total_day_pl += day_pl

    # Weights
    for item in enriched:
        item["weightPct"] = round(
            (item["marketValue"] / total_market_value * 100)
            if total_market_value > 0
            else 0,
            2,
        )

    # Sector allocations
    sector_map: dict[str, float] = {}
    for item in enriched:
        sector_map[item["sector"]] = sector_map.get(item["sector"], 0) + item["marketValue"]

    sector_allocations = [
        {
            "sector": s,
            "marketValue": round(v, 2),
            "weightPct": round(
                (v / total_market_value * 100) if total_market_value > 0 else 0, 2
            ),
        }
        for s, v in sorted(sector_map.items(), key=lambda x: -x[1])
    ]

    # Contributors / detractors
    sorted_by_pl = sorted(enriched, key=lambda x: x["unrealizedPL"])
    top_gainers = [
        {"ticker": x["ticker"], "contributionPct": x["weightPct"], "pl": x["unrealizedPL"]}
        for x in reversed(sorted_by_pl)
        if x["unrealizedPL"] > 0
    ][:3]
    top_losers = [
        {"ticker": x["ticker"], "contributionPct": x["weightPct"], "pl": x["unrealizedPL"]}
        for x in sorted_by_pl
        if x["unrealizedPL"] < 0
    ][:3]

    # Concentration
    sorted_by_weight = sorted(enriched, key=lambda x: -x["weightPct"])
    top_holding_wt = sorted_by_weight[0]["weightPct"] if sorted_by_weight else 0
    top3_wt = sum(x["weightPct"] for x in sorted_by_weight[:3])
    max_sector_wt = max((s["weightPct"] for s in sector_allocations), default=0)

    flags: list[str] = []
    if top_holding_wt > 25:
        flags.append("TOP_HOLDING_OVER_25")
    if top3_wt > 65:
        flags.append("TOP_3_OVER_65")
    if max_sector_wt > 40:
        flags.append("SECTOR_OVER_40")

    total_pl = total_market_value - total_cost_basis
    total_pl_pct = (total_pl / total_cost_basis * 100) if total_cost_basis > 0 else 0
    prior_value = total_market_value - total_day_pl
    day_pl_pct = (total_day_pl / prior_value * 100) if prior_value > 0 else 0

    return {
        "range": range_val,
        "asOf": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "marketValue": round(total_market_value, 2),
            "costBasis": round(total_cost_basis, 2),
            "unrealizedPL": round(total_pl, 2),
            "unrealizedPLPct": round(total_pl_pct, 2),
            "dayPL": round(total_day_pl, 2),
            "dayPLPct": round(day_pl_pct, 2),
        },
        "holdings": enriched,
        "sectorAllocations": sector_allocations,
        "contributors": {"topGainers": top_gainers, "topLosers": top_losers},
        "concentration": {
            "topHoldingWeightPct": round(top_holding_wt, 2),
            "top3WeightPct": round(top3_wt, 2),
            "maxSectorWeightPct": round(max_sector_wt, 2),
            "flags": flags,
        },
    }


# ─── Deterministic fallback bullets ──────────────────────────────────────────


def _build_deterministic_bullets(summary: dict) -> list[str]:
    """Build human-readable bullets from portfolio data, no AI required."""
    totals = summary["totals"]
    sectors = summary["sectorAllocations"]
    concentration = summary["concentration"]
    contributors = summary["contributors"]

    bullets: list[str] = []

    mv = totals["marketValue"]
    pl = totals["unrealizedPL"]
    pl_pct = totals["unrealizedPLPct"]
    direction = "gain" if pl >= 0 else "loss"
    bullets.append(
        f"Your portfolio has a total market value of ${mv:,.2f} "
        f"with an unrealized {direction} of ${abs(pl):,.2f} ({pl_pct:+.2f}%)."
    )

    if sectors:
        top = sectors[0]
        bullets.append(
            f"Your largest sector exposure is {top['sector']} "
            f"at {top['weightPct']:.1f}% of portfolio value."
        )

    gainers = contributors.get("topGainers", [])
    losers = contributors.get("topLosers", [])
    if gainers:
        g = gainers[0]
        bullets.append(
            f"Top contributor: {g['ticker']} with ${g['pl']:+,.2f} unrealized P/L."
        )
    if losers:
        l = losers[0]
        bullets.append(
            f"Largest detractor: {l['ticker']} with ${l['pl']:+,.2f} unrealized P/L."
        )

    flags = concentration.get("flags", [])
    if "TOP_HOLDING_OVER_25" in flags:
        bullets.append(
            f"Concentration note: your top holding represents "
            f"{concentration['topHoldingWeightPct']:.1f}% of portfolio value."
        )
    if "SECTOR_OVER_40" in flags:
        bullets.append(
            f"Sector concentration: your largest sector represents "
            f"{concentration['maxSectorWeightPct']:.1f}% of portfolio value."
        )

    return bullets[:5]


# ─── AI bullet generation ────────────────────────────────────────────────────


def _generate_ai_bullets(summary: dict) -> list[str] | None:
    """Call the AI model to produce portfolio bullets. Returns None on failure."""
    import httpx

    from app.services.ai.client import _BASE_URL, _MODEL, _TIMEOUT, _headers

    prompt = (
        "You are a portfolio analytics assistant. Based ONLY on the following "
        "portfolio data, generate 3-5 concise bullet points summarizing the portfolio.\n\n"
        "RULES:\n"
        "- Only restate numbers from the provided data. Do NOT invent or estimate any figures.\n"
        "- Use an educational, observational tone. Do NOT give investment advice.\n"
        "- Do NOT use words like 'should', 'recommend', 'buy', 'sell', or 'consider'.\n"
        "- Each bullet should be 1-2 sentences max.\n\n"
        f"PORTFOLIO DATA:\n{json.dumps(summary, indent=2)}\n\n"
        'Return a JSON object with a single key "bullets" containing an array of strings.'
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a portfolio analytics assistant that only restates "
                "provided numerical data. Never give investment advice."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    body = {
        "model": _MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_BASE_URL}/chat/completions",
                headers=_headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            bullets = parsed.get("bullets", [])
            if isinstance(bullets, list) and all(isinstance(b, str) for b in bullets):
                return bullets[:5]
    except Exception:
        logger.warning("AI bullet generation failed", exc_info=True)

    return None


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/summary")
def portfolio_summary(
    req: SummaryRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Compute full portfolio analytics from client-provided holdings."""
    if len(req.holdings) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 holdings supported.")
    return _compute_summary(req.holdings, req.range)


@router.post("/ai-brief")
def portfolio_ai_brief(
    req: AIBriefRequest,
    user: User = Depends(get_current_user),
) -> dict:
    """Generate an AI-powered portfolio brief grounded in computed data."""
    if len(req.holdings) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 holdings supported.")

    summary = _compute_summary(req.holdings, req.range)

    # Start with deterministic bullets as fallback
    bullets = _build_deterministic_bullets(summary)

    # Attempt AI-generated bullets
    try:
        ai_bullets = _generate_ai_bullets(summary)
        if ai_bullets:
            bullets = ai_bullets
    except Exception:
        logger.warning("AI brief generation failed, using fallback", exc_info=True)

    return {
        "bullets": bullets,
        "disclaimer": (
            "This analysis restates your portfolio data for informational "
            "purposes only. It is not personalized investment advice."
        ),
    }
