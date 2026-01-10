from Core.data_integrity import IntegrityPolicy, enforce_point_in_time, enforce_latency_buffer, clean_rows


def test_no_lookahead_point_in_time_blocks_future_known():
    policy = IntegrityPolicy(require_known_ts=True)
    decision = 1_000_000
    rows = [
        {"data_ts": 900_000, "known_ts": 950_000},
        {"data_ts": 900_000, "known_ts": 1_100_000},  # future-known -> must drop
    ]
    out = enforce_point_in_time(rows, decision, policy)
    assert len(out) == 1

def test_latency_buffer_blocks_too_recent_ticks():
    policy = IntegrityPolicy(latency_buffer_ms=500)
    decision = 10_000
    rows = [{"data_ts": 9_600}, {"data_ts": 9_700}]  # cutoff = 9_500
    out = enforce_latency_buffer(rows, decision, policy)
    assert out == []

def test_clean_quotes_reject_crossed():
    policy = IntegrityPolicy()
    rows = [
        {"bid": 10, "ask": 11, "bid_size": 1, "ask_size": 1, "integrity_grade": "A"},
        {"bid": 10, "ask":  9, "bid_size": 1, "ask_size": 1, "integrity_grade": "A"},
    ]
    out = clean_rows("quote", rows, policy, mode="live")
    assert len(out) == 1

def test_backtest_rejects_reconstructed_by_default():
    policy = IntegrityPolicy(allow_reconstructed_in_backtests=False)
    rows = [
        {"o":1,"h":1,"l":1,"c":1,"v":1, "is_reconstructed": False, "integrity_grade":"A"},
        {"o":1,"h":1,"l":1,"c":1,"v":1, "is_reconstructed": True,  "integrity_grade":"A"},
    ]
    out = clean_rows("bar", rows, policy, mode="backtest")
    assert len(out) == 1
