from _bootstrap import bootstrap
bootstrap()

from App.rules import load_rules, check_order

def run_case(name: str, order: dict, rules: dict, expect_ok: bool):
    result = check_order(order, rules)
    status = "PASS" if result.ok == expect_ok else "FAIL"
    print(f"\n=== {name} ===")
    print(f"Expected OK: {expect_ok} | Got OK: {result.ok} -> {status}")
    if result.reasons:
        print("Reasons:")
        for r in result.reasons:
            print(f" - {r}")
    else:
        print("Reasons: []")

def main():
    rules = load_rules("ips_rules.yaml")

    base_order = {
        "asset_class": "etfs",
        "symbol": "SPY",
        "instrument_type": "etf",
        "order_type": "limit",
        "venue_type": "lit",
        "liquidity": {"is_thin": False, "is_wide_spread": False},
        "behavior_flags": [],
    }

    # 1) Good order should PASS
    run_case("GOOD: ETF limit order", dict(base_order), rules, expect_ok=True)

    # 2) Disallowed order type should FAIL (stop-market is banned)
    o2 = dict(base_order)
    o2["order_type"] = "stop_market"
    run_case("BAD: stop-market order type", o2, rules, expect_ok=False)

    # 3) Crypto should FAIL if crypto.allowed is false
    o3 = dict(base_order)
    o3["asset_class"] = "crypto_spot"
    o3["instrument_type"] = "crypto_spot"
    o3["symbol"] = "BTCUSD"
    run_case("BAD: crypto while crypto.allowed=false", o3, rules, expect_ok=False)

    # 4) Market order in thin liquidity should FAIL if enabled in YAML
    o4 = dict(base_order)
    o4["order_type"] = "market"
    o4["liquidity"] = {"is_thin": True, "is_wide_spread": False}
    run_case("BAD: market order in thin liquidity", o4, rules, expect_ok=False)

    # 5) Wide spread should FAIL if no_aggressive_crossing_in_wide_spreads=true
    o5 = dict(base_order)
    o5["liquidity"] = {"is_thin": False, "is_wide_spread": True}
    run_case("BAD: wide spread blocked", o5, rules, expect_ok=False)

    # 6) Prohibited instrument test (OTC penny stocks)
    o6 = dict(base_order)
    o6["instrument_type"] = "otc_penny_stocks"
    o6["symbol"] = "FAKE"
    run_case("BAD: prohibited instrument otc_penny_stocks", o6, rules, expect_ok=False)

if __name__ == "__main__":
    main()