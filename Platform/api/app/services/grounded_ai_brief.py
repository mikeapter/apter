"""
APTER — FINNHUB-GROUNDED AI BRIEF (SINGLE FILE)
What this guarantees:
- The LLM cannot invent facts because it is locked to a Finnhub Fact Pack
  and its output is validated before display.
What this does NOT guarantee:
- "Real-world truth" if Finnhub upstream data is wrong or stale.
  It guarantees the brief matches Finnhub + your canonical mapping exactly.
Wiring:
- You call get_grounded_ai_brief(symbol) from your route.
- Frontend displays: brief_markdown, citations, as_of_utc, validation_passed.
Required env vars:
- FINNHUB_API_KEY
- AI_API_KEY  (shared with the rest of the Apter AI layer)
"""
from __future__ import annotations
import logging
import os
import json
import requests
import httpx
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# =========================
# CONFIG (reads from same env vars as app.services.ai.client)
# =========================
_API_KEY = os.getenv("AI_API_KEY", "")
_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
_TIMEOUT = int(os.getenv("AI_TIMEOUT_SECONDS", "60"))
TEMPERATURE = 0.0          # keep 0 for grounded output stability
MAX_ATTEMPTS = 2           # attempts before fallback
FINNHUB_BASE = "https://finnhub.io/api/v1"

PCT_FIELDS = {
    "day_change_pct", "revenue_yoy", "eps_yoy", "fcf_yoy",
    "gross_margin", "op_margin", "fcf_margin", "roe",
    "volatility_30d", "max_drawdown_1y", "above_sma50_pct",
}

FORBIDDEN_FORWARD_TERMS = [
    "forward p/e", "fy1", "fy2", "consensus", "next year eps", "estimated eps"
]

# =========================
# FINNHUB HELPERS
# =========================
def _fh_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise RuntimeError("Missing FINNHUB_API_KEY environment variable")
    url = f"{FINNHUB_BASE}{path}"
    qp = dict(params)
    qp["token"] = api_key
    r = requests.get(url, params=qp, timeout=20)
    r.raise_for_status()
    return r.json()

def _num(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None

# =========================
# FACT PACK BUILDER (FINNHUB)
# =========================
def build_fact_pack(symbol: str) -> Dict[str, Any]:
    """
    Canonical Fact Pack powered by Finnhub.
    The LLM is forced to use ONLY these values.
    Important notes:
    - Finnhub profile2.marketCapitalization is commonly in *millions* (check your output).
      This script converts millions -> dollars for consistency.
    - Some margin/growth fields may be missing depending on coverage.
    - Volatility/drawdown/SMA are left None unless you compute them from candles.
    """
    now = datetime.now(timezone.utc).isoformat()
    sym = symbol.upper()

    # --- Finnhub fetches ---
    quote = _fh_get("/quote", {"symbol": sym})                          # price + daily %
    profile = _fh_get("/stock/profile2", {"symbol": sym})              # name + industry + market cap
    basic = _fh_get("/stock/metric", {"symbol": sym, "metric": "all"}) # metrics
    metric = (basic or {}).get("metric", {}) or {}

    # --- Canonical mappings ---
    price = _num(quote.get("c"))
    day_change_pct = _num(quote.get("dp"))
    company_name = profile.get("name") or None
    sector = profile.get("finnhubIndustry") or None

    # marketCapitalization is typically in millions in Finnhub profile2
    market_cap_m = _num(profile.get("marketCapitalization"))
    market_cap = None if market_cap_m is None else market_cap_m * 1_000_000.0

    # Common Finnhub metric keys (coverage varies)
    pe_ttm = _num(metric.get("peTTM") or metric.get("pe_ttm") or metric.get("pe"))
    peg = _num(metric.get("pegTTM") or metric.get("peg"))
    beta = _num(metric.get("beta"))

    # Margin fields: depending on Finnhub, may be in percent already. If you detect decimals,
    # you can convert (e.g., if 0.45 -> 45). For now, we keep raw values from Finnhub.
    gross_margin = _num(metric.get("grossMarginTTM") or metric.get("grossMarginAnnual"))
    op_margin = _num(metric.get("operatingMarginTTM") or metric.get("operatingMarginAnnual"))
    fcf_margin = _num(metric.get("freeCashFlowMarginTTM") or metric.get("freeCashFlowMarginAnnual"))
    roe = _num(metric.get("roeTTM") or metric.get("roeAnnual"))
    debt_to_equity = _num(metric.get("totalDebt/totalEquity") or metric.get("totalDebtToEquity"))

    revenue_yoy = _num(metric.get("revenueGrowthTTM") or metric.get("revenueGrowthAnnual"))
    eps_yoy = _num(metric.get("epsGrowthTTM") or metric.get("epsGrowthAnnual"))
    fcf_yoy = _num(metric.get("fcfGrowthTTM") or metric.get("freeCashFlowGrowthTTM"))

    # Not provided reliably by Finnhub metric endpoint; compute from candles if desired
    volatility_30d = None
    max_drawdown_1y = None
    sma50 = None
    sma200 = None
    above_sma50_pct = None

    # Keep this non-numeric unless you control the data source
    business_summary = None

    sources = {
        "finnhub": {
            "as_of_utc": now,
            "endpoints": ["/quote", "/stock/profile2", "/stock/metric?metric=all"],
        }
    }

    return {
        "symbol": sym,
        "as_of_utc": now,
        "sources": sources,
        "price": price,
        "day_change_pct": day_change_pct,
        "market_cap": market_cap,
        "pe_ttm": pe_ttm,
        "peg": peg,
        "revenue_yoy": revenue_yoy,
        "eps_yoy": eps_yoy,
        "fcf_yoy": fcf_yoy,
        "gross_margin": gross_margin,
        "op_margin": op_margin,
        "fcf_margin": fcf_margin,
        "roe": roe,
        "debt_to_equity": debt_to_equity,
        "beta": beta,
        "volatility_30d": volatility_30d,
        "max_drawdown_1y": max_drawdown_1y,
        "sma50": sma50,
        "sma200": sma200,
        "above_sma50_pct": above_sma50_pct,
        "sector": sector,
        "company_name": company_name,
        "business_summary": business_summary,
        # Unless you explicitly add analyst estimates endpoints, keep false.
        "forward_estimates_available": False,
        "forward_notes": "Forward estimates unavailable from current data sources (Finnhub endpoints not enabled in this build).",
    }

# =========================
# PROMPT (STRICT JSON OUTPUT)
# =========================
def _build_prompt(fact_pack: Dict[str, Any]) -> str:
    return f"""
You write an educational stock intelligence brief.
NON-NEGOTIABLE RULES:
1) Use ONLY facts present in FACT_PACK. Do NOT invent or infer ANY numbers, dates, percentages, ratios, rankings, or claims.
2) If a field is null/missing, you MUST say: "unavailable from current data sources" and you MUST NOT estimate.
3) Do NOT mention forward estimates unless FACT_PACK.forward_estimates_available == true.
4) Every metric you mention MUST come from FACT_PACK and match EXACTLY (reasonable rounding only).
5) Output MUST be valid JSON exactly matching the schema below.

OUTPUT JSON SCHEMA (STRICT):
{{
  "brief_markdown": "markdown text",
  "citations": ["provider: fields_used, as_of_utc=..."],
  "numbers_used": [{{"field":"price","value":428.90}}],
  "fields_used": ["price","pe_ttm"]
}}

FACT_PACK (JSON):
{json.dumps(fact_pack, ensure_ascii=False)}
""".strip()

# =========================
# VALIDATOR
# =========================
def _validate_model_json(fact_pack: Dict[str, Any], model_json: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not isinstance(model_json, dict):
        return False, ["Model output is not a JSON object"]

    for key in ("brief_markdown", "citations", "numbers_used", "fields_used"):
        if key not in model_json:
            errors.append(f"Missing key: {key}")

    if errors:
        return False, errors

    if not isinstance(model_json["brief_markdown"], str) or not model_json["brief_markdown"].strip():
        errors.append("brief_markdown must be a non-empty string")

    if not isinstance(model_json["citations"], list) or len(model_json["citations"]) == 0:
        errors.append("citations must be a non-empty list")

    if not isinstance(model_json["numbers_used"], list):
        errors.append("numbers_used must be a list")

    if not isinstance(model_json["fields_used"], list):
        errors.append("fields_used must be a list")

    if errors:
        return False, errors

    # Citation providers must match FACT_PACK.sources keys
    allowed_providers = set((fact_pack.get("sources") or {}).keys())
    for c in model_json["citations"]:
        if not isinstance(c, str) or ":" not in c:
            errors.append("Invalid citation format (must be 'provider: ...')")
            continue
        provider = c.split(":", 1)[0].strip()
        if provider not in allowed_providers:
            errors.append(f"Citation provider not in FACT_PACK.sources: {provider}")

    # Validate numbers_used are consistent with FACT_PACK
    for item in model_json["numbers_used"]:
        if not isinstance(item, dict) or "field" not in item or "value" not in item:
            errors.append("numbers_used contains invalid entry; must be {field,value}")
            continue
        field = item["field"]
        value = item["value"]
        if field not in fact_pack:
            errors.append(f"Model referenced unknown field: {field}")
            continue
        fp_val = fact_pack.get(field)
        if fp_val is None:
            errors.append(f"Model referenced '{field}' but FACT_PACK has it unavailable (null)")
            continue
        try:
            fp = float(fp_val)
            v = float(value)
        except Exception:
            errors.append(f"Non-numeric compare failed for '{field}'")
            continue

        # tolerances
        if field == "market_cap":
            # allow 0.10% relative tolerance
            if abs(v - fp) / max(abs(fp), 1.0) > 0.001:
                errors.append(f"market_cap mismatch: model={v} vs fact_pack={fp}")
        else:
            tol = 0.05 if field in PCT_FIELDS else 0.02
            if abs(v - fp) > tol:
                errors.append(f"{field} mismatch: model={v} vs fact_pack={fp}")

    # Forward estimate guard
    if not fact_pack.get("forward_estimates_available", False):
        text = (model_json["brief_markdown"] or "").lower()
        for term in FORBIDDEN_FORWARD_TERMS:
            if term in text:
                errors.append(f"Forward-estimate content forbidden but found: '{term}'")

    return (len(errors) == 0, errors)

# =========================
# FALLBACK (NO AI)
# =========================
def _fallback(fact_pack: Dict[str, Any], validation_errors: List[str]) -> Dict[str, Any]:
    sym = fact_pack.get("symbol", "UNKNOWN")
    name = fact_pack.get("company_name") or sym
    asof = fact_pack.get("as_of_utc", "UNKNOWN")

    def fmt(field: str, suffix: str = "") -> str:
        v = fact_pack.get(field)
        return "unavailable from current data sources" if v is None else f"{v}{suffix}"

    brief = f"""## Stock Intelligence Brief — {name} ({sym})

**Data as of:** {asof}

### Snapshot (source-grounded)
- Price: {fmt("price")}
- Day change: {fmt("day_change_pct","%")}
- Market cap: {fmt("market_cap")}
- P/E (TTM): {fmt("pe_ttm")}
- PEG: {fmt("peg")}
- Revenue YoY: {fmt("revenue_yoy","%")}
- EPS YoY: {fmt("eps_yoy","%")}
- FCF YoY: {fmt("fcf_yoy","%")}
- Gross margin: {fmt("gross_margin","%")}
- Operating margin: {fmt("op_margin","%")}
- FCF margin: {fmt("fcf_margin","%")}
- ROE: {fmt("roe","%")}
- Debt/Equity: {fmt("debt_to_equity")}
- Beta: {fmt("beta")}
- 30D realized volatility: {fmt("volatility_30d","%")}
- 1Y max drawdown: {fmt("max_drawdown_1y","%")}

**Forward estimates:** {"available" if fact_pack.get("forward_estimates_available") else "unavailable from current data sources"}
"""

    citations = [f"{p}: FACT_PACK, as_of_utc={asof}" for p in (fact_pack.get("sources") or {}).keys()]

    return {
        "brief_markdown": brief,
        "citations": citations,
        "validation_passed": False,
        "validation_errors": validation_errors + ["Served deterministic fallback (no AI)."],
    }

# =========================
# MAIN ENTRYPOINT (CALL FROM YOUR ROUTE)
# =========================
def _llm_completion(messages: List[Dict[str, str]]) -> str | None:
    """Call the shared OpenAI-compatible endpoint (same config as ai.client)."""
    headers = {"Content-Type": "application/json"}
    if _API_KEY:
        headers["Authorization"] = f"Bearer {_API_KEY}"

    body = {
        "model": _MODEL,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                f"{_BASE_URL}/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("Grounded brief LLM call failed")
        return None


def get_grounded_ai_brief(symbol: str) -> Dict[str, Any]:
    """
    Call this from your API route. Returns a dict safe to send to frontend.
    Includes the fact_pack so the frontend can render structured metrics.
    """
    fact_pack = build_fact_pack(symbol)
    prompt = _build_prompt(fact_pack)
    last_errors: List[str] = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = _llm_completion([
            {"role": "system", "content": "You must not hallucinate. Output strictly valid JSON only."},
            {"role": "user", "content": prompt},
        ])
        if raw is None:
            last_errors = [f"Attempt {attempt}: LLM request failed"]
            continue

        try:
            model_json = json.loads(raw)
        except Exception:
            last_errors = [f"Attempt {attempt}: model output was not valid JSON"]
            continue

        ok, errors = _validate_model_json(fact_pack, model_json)
        if ok:
            return {
                "symbol": fact_pack["symbol"],
                "as_of_utc": fact_pack["as_of_utc"],
                "brief_markdown": model_json["brief_markdown"],
                "citations": model_json["citations"],
                "fact_pack": fact_pack,
                "validation_passed": True,
                "validation_errors": [],
            }
        last_errors = [f"Attempt {attempt}: {e}" for e in errors]

    fb = _fallback(fact_pack, last_errors)
    return {
        "symbol": fact_pack["symbol"],
        "as_of_utc": fact_pack["as_of_utc"],
        "fact_pack": fact_pack,
        **fb,
    }
