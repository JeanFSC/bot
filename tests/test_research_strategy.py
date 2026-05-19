import pandas as pd

from mt5_bot.research_backtest import run_research_backtest
from mt5_bot.research_strategy import detect_research_signal


def _rates(closes):
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=len(closes), freq="5min"),
        "open": [c - 0.00005 for c in closes],
        "high": [c + 0.0002 for c in closes],
        "low": [c - 0.0002 for c in closes],
        "close": closes,
        "tick_volume": [100] * len(closes),
        "real_volume": [0] * len(closes),
    })


def test_detect_research_signal_returns_none_on_short_data():
    signal = detect_research_signal(_rates([1.1, 1.2]), "EURUSD")

    assert signal.type.value == "NONE"
    assert signal.reason == "not_enough_bars"


def test_run_research_backtest_returns_metrics():
    closes = []
    closes.extend([1.1000 + (0.00002 if i % 2 else -0.00002) for i in range(90)])
    closes.extend([1.1000 + i * 0.00012 for i in range(80)])
    rates = _rates(closes)

    result = run_research_backtest(rates, "EURUSD", lookback=24, max_hold_bars=12)

    assert result.symbol == "EURUSD"
    assert result.trades >= 0
    assert isinstance(result.trades_detail, list)
