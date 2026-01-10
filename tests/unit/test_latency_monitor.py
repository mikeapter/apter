from Core.latency_monitor import LatencyMonitor, LatencySla, SlaBand

def make_sla():
    return LatencySla(
        quote_age_ms=SlaBand(warn=250, outage=1000),
        heartbeat_gap_ms=SlaBand(warn=1500, outage=5000),
        order_ack_ms=SlaBand(warn=750, outage=2000),
        breaches_to_enter_warn=2,
        breaches_to_enter_outage=2,
        ok_samples_to_recover=3,
        failover_enabled=True,
        failover_outage_grace_ms=3000,
    )

def test_warn_then_outage_on_stale_quote():
    sla = make_sla()
    m = LatencyMonitor(sla)
    now = 100000

    # quote gets old enough for WARN twice => WARN
    m.update_quote("AAPL", data_ts_ms=now-100, received_ts_ms=now-300)
    m.evaluate(now_ts_ms=now)
    d = m.evaluate(now_ts_ms=now)
    assert d.mode == "WARN"
    assert d.allow_market_orders is False

    # quote old enough for OUTAGE twice => OUTAGE
    m.update_quote("AAPL", data_ts_ms=now-100, received_ts_ms=now-2000)
    m.evaluate(now_ts_ms=now)
    d2 = m.evaluate(now_ts_ms=now)
    assert d2.mode == "OUTAGE"
    assert d2.can_open_new_risk is False
    assert d2.allow_only_reduce_risk is True

def test_failover_after_grace():
    sla = make_sla()
    m = LatencyMonitor(sla)
    now = 200000

    # force OUTAGE
    m.update_quote("SPY", data_ts_ms=now-100, received_ts_ms=now-3000)
    m.evaluate(now_ts_ms=now)
    d = m.evaluate(now_ts_ms=now)
    assert d.mode == "OUTAGE"

    # before grace -> no failover
    d2 = m.evaluate(now_ts_ms=now + 2000)
    assert d2.request_failover is False

    # after grace -> failover requested
    d3 = m.evaluate(now_ts_ms=now + 4000)
    assert d3.request_failover is True

def test_recover_to_ok_after_clean_samples():
    sla = make_sla()
    m = LatencyMonitor(sla)
    now = 300000

    # enter WARN
    m.update_quote("TSLA", data_ts_ms=now-50, received_ts_ms=now-400)
    m.evaluate(now_ts_ms=now)
    d = m.evaluate(now_ts_ms=now)
    assert d.mode == "WARN"

    # fresh quotes => recover after 3 clean samples
    for i in range(3):
        m.update_quote("TSLA", data_ts_ms=now+i*10, received_ts_ms=now+i*10)
        d = m.evaluate(now_ts_ms=now+i*10)
    assert d.mode == "OK"
