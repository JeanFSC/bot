from datetime import datetime, timezone

import pandas as pd

from mt5_bot.strategy import SignalType, StrategyConfig, detect_signal


def _rates(closes):
    return pd.DataFrame(
        {
            "time": [datetime(2026, 1, 1, 0, i, tzinfo=timezone.utc) for i in range(len(closes))],
            "open": closes,
            "high": [price + 0.0002 for price in closes],
            "low": [price - 0.0002 for price in closes],
            "close": closes,
            "tick_volume": [100] * len(closes),
            "spread": [8] * len(closes),
            "real_volume": [100] * len(closes),
        }
    )


def test_detect_signal_ignores_current_unclosed_bar():
    candles = [1.1000] * 30 + [1.0998, 1.0996, 1.1030]
    signal = detect_signal(_rates(candles), StrategyConfig(fast_ema=3, slow_ema=5, use_rsi_filter=False, use_atr_filter=False))

    assert signal.type is SignalType.NONE
    assert signal.reason == "no_closed_bar_crossover"


def test_detect_signal_returns_buy_on_closed_ema_cross_above():
    candles = [1.1000] * 30 + [1.0990, 1.1018, 1.1019]
    signal = detect_signal(_rates(candles), StrategyConfig(fast_ema=3, slow_ema=5, use_rsi_filter=False, use_atr_filter=False))

    assert signal.type is SignalType.BUY
    assert signal.price == 1.1018


def test_detect_signal_blocks_buy_when_rsi_is_overbought():
    candles = [1.1000] * 30 + [1.0990, 1.1040, 1.1041]
    config = StrategyConfig(fast_ema=3, slow_ema=5, use_atr_filter=False, rsi_buy_max=60)

    signal = detect_signal(_rates(candles), config)

    assert signal.type is SignalType.NONE
    assert signal.reason == "rsi_buy_filter"
