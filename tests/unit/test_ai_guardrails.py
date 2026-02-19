"""
Tests for AI guardrails — non-RIA compliance validator.

Run: cd Platform/api && python -m pytest ../../tests/unit/test_ai_guardrails.py -v
Or:  pytest tests/unit/test_ai_guardrails.py -v  (from repo root with PYTHONPATH set)
"""
import sys
import os

# Add Platform/api to path so we can import app modules
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "Platform", "api")
)

import pytest

from app.services.ai.guardrails import validate_ai_output, _scan_text


# ---------------------------------------------------------------------------
# Helper: build a valid, compliant response dict
# ---------------------------------------------------------------------------


def _compliant_response(**overrides):
    base = {
        "summary": "The S&P 500 is trading near recent highs with moderate breadth.",
        "data_used": ["S&P 500 index data"],
        "explanation": "Market conditions show low volatility relative to historical averages.",
        "watchlist_items": ["SPY"],
        "risk_flags": ["Concentration risk in top-weighted index constituents"],
        "checklist": ["Monitor VIX for regime changes", "Review sector rotation patterns"],
        "disclaimer": "Educational information only — not investment advice.",
        "citations": [],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Test: compliant responses pass validation
# ---------------------------------------------------------------------------


class TestCompliantResponses:
    def test_fully_compliant(self):
        result = validate_ai_output(_compliant_response())
        assert result.ok is True
        assert result.violations == []

    def test_compliant_with_scenarios(self):
        result = validate_ai_output(
            _compliant_response(
                scenarios=[
                    "If volatility expands, breadth may narrow further",
                    "If earnings growth accelerates, valuations may compress on higher base",
                ]
            )
        )
        assert result.ok is True

    def test_compliant_with_comparisons(self):
        result = validate_ai_output(
            _compliant_response(
                comparisons=[
                    "AAPL trades at 29x vs sector median of 25x",
                    "MSFT Azure growth of 32% vs AWS growth of 28%",
                ]
            )
        )
        assert result.ok is True


# ---------------------------------------------------------------------------
# Test: advice / action language is flagged
# ---------------------------------------------------------------------------


class TestAdviceActionLanguage:
    @pytest.mark.parametrize(
        "phrase",
        [
            "You should consider buying this stock",
            "I recommend adding to your position",
            "I suggest taking a closer look at AAPL",
            "The best move here is to wait",
            "Now is the perfect time to enter",
            "Time to buy before earnings",
        ],
    )
    def test_advice_phrases_flagged(self, phrase):
        resp = _compliant_response(explanation=phrase)
        result = validate_ai_output(resp)
        assert result.ok is False
        assert len(result.violations) > 0

    @pytest.mark.parametrize(
        "word",
        ["buy", "sell", "hold", "accumulate", "dump", "trim", "short"],
    )
    def test_action_words_flagged(self, word):
        resp = _compliant_response(
            summary=f"Investors may want to {word} shares in this environment."
        )
        result = validate_ai_output(resp)
        assert result.ok is False

    def test_take_profit_flagged(self):
        resp = _compliant_response(
            checklist=["Take profit at current levels"]
        )
        result = validate_ai_output(resp)
        assert result.ok is False

    def test_stop_loss_flagged(self):
        resp = _compliant_response(
            checklist=["Set a stop loss at 5% below entry"]
        )
        result = validate_ai_output(resp)
        assert result.ok is False


# ---------------------------------------------------------------------------
# Test: portfolio / allocation guidance is flagged
# ---------------------------------------------------------------------------


class TestPortfolioGuidance:
    def test_rebalance_flagged(self):
        resp = _compliant_response(
            explanation="You should rebalance your portfolio quarterly."
        )
        result = validate_ai_output(resp)
        assert result.ok is False

    def test_allocate_flagged(self):
        resp = _compliant_response(
            explanation="Allocate 60% to equities and 40% to bonds."
        )
        result = validate_ai_output(resp)
        assert result.ok is False

    def test_position_sizing_flagged(self):
        resp = _compliant_response(
            explanation="Position sizing should be 2% of total portfolio."
        )
        result = validate_ai_output(resp)
        assert result.ok is False

    def test_your_portfolio_flagged(self):
        resp = _compliant_response(
            explanation="Based on your portfolio, tech exposure is high."
        )
        result = validate_ai_output(resp)
        assert result.ok is False

    def test_put_percent_in_flagged(self):
        resp = _compliant_response(
            explanation="Consider putting 30% in technology sector."
        )
        result = validate_ai_output(resp)
        assert result.ok is False


# ---------------------------------------------------------------------------
# Test: suitability / personalization is flagged
# ---------------------------------------------------------------------------


class TestSuitability:
    def test_risk_tolerance_flagged(self):
        resp = _compliant_response(
            explanation="Based on your risk tolerance, this may not be suitable."
        )
        result = validate_ai_output(resp)
        assert result.ok is False

    def test_given_your_situation_flagged(self):
        resp = _compliant_response(
            explanation="Given your situation, a conservative approach makes sense."
        )
        result = validate_ai_output(resp)
        assert result.ok is False

    def test_for_someone_like_you_flagged(self):
        resp = _compliant_response(
            explanation="For someone like you, growth stocks may be appropriate."
        )
        result = validate_ai_output(resp)
        assert result.ok is False

    def test_your_retirement_flagged(self):
        resp = _compliant_response(
            explanation="For your retirement, consider diversification."
        )
        result = validate_ai_output(resp)
        assert result.ok is False


# ---------------------------------------------------------------------------
# Test: overconfidence / guarantee claims are flagged
# ---------------------------------------------------------------------------


class TestOverconfidence:
    @pytest.mark.parametrize(
        "phrase",
        [
            "This is a guaranteed winner",
            "This is a can't miss opportunity",
            "It's a sure thing at these levels",
            "This is essentially risk-free",
            "The stock will definitely go up",
            "It will go up from here",
            "This will outperform the market",
        ],
    )
    def test_overconfidence_flagged(self, phrase):
        resp = _compliant_response(summary=phrase)
        result = validate_ai_output(resp)
        assert result.ok is False


# ---------------------------------------------------------------------------
# Test: missing disclaimer is flagged
# ---------------------------------------------------------------------------


class TestDisclaimer:
    def test_missing_disclaimer_flagged(self):
        resp = _compliant_response(disclaimer="")
        result = validate_ai_output(resp)
        assert result.ok is False
        assert any("missing_disclaimer" in v for v in result.violations)

    def test_wrong_disclaimer_flagged(self):
        resp = _compliant_response(disclaimer="Not financial advice.")
        result = validate_ai_output(resp)
        assert result.ok is False

    def test_correct_disclaimer_passes(self):
        resp = _compliant_response(
            disclaimer="Educational information only — not investment advice."
        )
        result = validate_ai_output(resp)
        assert result.ok is True


# ---------------------------------------------------------------------------
# Test: invalid JSON is handled
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_invalid_json_string(self):
        result = validate_ai_output("this is not json{{{")
        assert result.ok is False
        assert any("invalid_json" in v for v in result.violations)

    def test_valid_json_string(self):
        import json

        resp = _compliant_response()
        result = validate_ai_output(json.dumps(resp))
        assert result.ok is True

    def test_scan_text_empty(self):
        violations = _scan_text("")
        assert violations == []

    def test_scan_text_clean(self):
        violations = _scan_text(
            "The S&P 500 shows moderate momentum with RSI at 55."
        )
        assert violations == []

    def test_scan_text_violating(self):
        violations = _scan_text("You should definitely buy more shares now.")
        assert len(violations) > 0
