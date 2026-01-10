import tempfile
from Core.strategy_eligibility_mask import StrategyEligibilityMask, load_strategy_eligibility_mask


def test_prohibit_wins_over_allow():
    mask = StrategyEligibilityMask(
        regimes={
            "RANGE": {
                "allow": ["MEAN_*"],
                "prohibit": ["MEAN_REVERSION"],
            }
        },
        default_policy="PROHIBIT",
        min_confidence_to_trade=0.60,
    )

    d1 = mask.decide("RANGE", "MEAN_REVERSION", confidence=0.90)
    assert d1.allowed is False
    assert "prohibited" in d1.reason

    d2 = mask.decide("RANGE", "MEAN_SCALP", confidence=0.90)
    assert d2.allowed is True


def test_allow_list_requires_match():
    mask = StrategyEligibilityMask(
        regimes={"TREND_UP": {"allow": ["TREND_FOLLOW"]}},
        default_policy="ALLOW",
        min_confidence_to_trade=0.60,
    )

    assert mask.decide("TREND_UP", "TREND_FOLLOW", confidence=0.90).allowed is True
    assert mask.decide("TREND_UP", "MEAN_REVERSION", confidence=0.90).allowed is False


def test_default_policy_prohibit_for_unknown_regime():
    mask = StrategyEligibilityMask(regimes={}, default_policy="PROHIBIT", min_confidence_to_trade=0.60)
    assert mask.decide("UNKNOWN", "ANY_STRATEGY", confidence=0.90).allowed is False


def test_confidence_hard_gate_blocks_all():
    mask = StrategyEligibilityMask(
        regimes={"RANGE": {"allow": ["*"]}},
        default_policy="ALLOW",
        min_confidence_to_trade=0.80,
    )
    d = mask.decide("RANGE", "MEAN_REVERSION", confidence=0.50)
    assert d.allowed is False
    assert "confidence" in d.reason


def test_yaml_loader_smoke():
    yaml_text = """
version: 1
default_policy: PROHIBIT
min_confidence_to_trade: 0.60
regimes:
  RANGE:
    allow: ["MEAN_*"]
    prohibit: ["TREND_*"]
"""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as f:
        f.write(yaml_text)
        path = f.name

    mask = load_strategy_eligibility_mask(path)
    assert mask.decide("RANGE", "MEAN_REVERSION", confidence=0.90).allowed is True
    assert mask.decide("RANGE", "TREND_FOLLOW", confidence=0.90).allowed is False
