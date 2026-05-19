import pandas as pd

from mt5_bot.market_structure import anchored_vwap, classify_market_state, volume_profile


def _rates(closes, volumes=None):
    if volumes is None:
        volumes = [100] * len(closes)
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=len(closes), freq="5min"),
        "open": closes,
        "high": [c + 0.0002 for c in closes],
        "low": [c - 0.0002 for c in closes],
        "close": closes,
        "tick_volume": volumes,
        "real_volume": [0] * len(closes),
    })


def test_anchored_vwap_uses_volume_weighting():
    rates = _rates([1.0, 2.0, 4.0], [1, 1, 2])

    result = anchored_vwap(rates)

    assert round(float(result.iloc[-1]), 4) == 2.75


def test_volume_profile_returns_poc_near_high_volume_area():
    rates = _rates([1.0, 1.01, 1.02, 1.50, 1.51, 1.52], [10, 10, 10, 200, 200, 200])

    profile = volume_profile(rates, bins=6)

    assert profile.poc > 1.3
    assert profile.hvn
    assert profile.lvn


def test_classify_market_state_detects_upside_imbalance():
    closes = [1.1000 + i * 0.00001 for i in range(70)]
    closes += [1.1030, 1.1080]
    rates = _rates(closes)

    assert classify_market_state(rates, "EURUSD", lookback=24) == "imbalance_up"


def test_classify_market_state_detects_balance():
    closes = [1.1000 + (0.00003 if i % 2 else -0.00003) for i in range(80)]
    rates = _rates(closes)

    assert classify_market_state(rates, "EURUSD", lookback=24) == "balance"
