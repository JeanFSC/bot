from mt5_bot.safety import equity_stop_decision


def test_equity_stop_decision_stops_at_floor():
    decision = equity_stop_decision(equity=74_999.99, target_equity=200_000, floor_equity=75_000)

    assert decision.stop
    assert decision.reason == "floor_equity_hit"


def test_equity_stop_decision_stops_at_target():
    decision = equity_stop_decision(equity=200_000, target_equity=200_000, floor_equity=75_000)

    assert decision.stop
    assert decision.reason == "target_equity_hit"


def test_equity_stop_decision_continues_between_floor_and_target():
    decision = equity_stop_decision(equity=100_000, target_equity=200_000, floor_equity=75_000)

    assert not decision.stop
    assert decision.reason is None
