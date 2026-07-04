from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd

from mt5_bot.replay import render_replay_markdown, summarize_backtest, write_replay_report


def _rates():
    closes = [1.1000 + i * 0.0001 for i in range(80)]
    return pd.DataFrame(
        {
            "time": pd.date_range("2026-01-01", periods=len(closes), freq="5min"),
            "open": closes,
            "high": [c + 0.0002 for c in closes],
            "low": [c - 0.0002 for c in closes],
            "close": closes,
        }
    )


def test_summarize_backtest_returns_replay_summary():
    config = SimpleNamespace(
        symbol="EURUSD",
        timeframe="M5",
        strategy=SimpleNamespace(
            fast_ema=3,
            slow_ema=5,
            trend_ema=10,
            use_trend_filter=False,
            rsi_period=14,
            rsi_buy_max=70,
            rsi_sell_min=30,
            use_rsi_filter=False,
            atr_period=14,
            min_atr_pips=0.1,
            use_atr_filter=False,
            atr_sl_multiplier=1.5,
            atr_tp_multiplier=3.0,
            use_atr_sl_tp=False,
            session_start_hour=0,
            session_end_hour=24,
            use_session_filter=False,
            session2_start_hour=0,
            session2_end_hour=0,
            use_session2=False,
            adx_period=14,
            adx_min_value=10,
            use_adx_filter=False,
            use_rsi_momentum=False,
            use_trailing_stop=False,
            breakeven_atr_multiplier=1.0,
            trailing_atr_multiplier=1.5,
            use_retest_filter=False,
            retest_timeout_bars=4,
            use_candle_confirm=False,
        ),
    )
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    summary = summarize_backtest("config/demo.yaml", config, _rates(), now, now)

    assert summary.symbol == "EURUSD"
    assert summary.status == "ok"


def test_write_replay_report_creates_files(tmp_path):
    summary = summarize_backtest(
        "config/demo.yaml",
        SimpleNamespace(symbol="EURUSD", timeframe="M5", strategy=SimpleNamespace(**_strategy_defaults())),
        _rates(),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    result = write_replay_report([summary], tmp_path)

    assert result["json_path"].exists()
    assert result["csv_path"].exists()
    assert "EURUSD" in render_replay_markdown([summary])


def _strategy_defaults():
    return {
        "fast_ema": 3,
        "slow_ema": 5,
        "trend_ema": 10,
        "use_trend_filter": False,
        "rsi_period": 14,
        "rsi_buy_max": 70,
        "rsi_sell_min": 30,
        "use_rsi_filter": False,
        "atr_period": 14,
        "min_atr_pips": 0.1,
        "use_atr_filter": False,
        "atr_sl_multiplier": 1.5,
        "atr_tp_multiplier": 3.0,
        "use_atr_sl_tp": False,
        "session_start_hour": 0,
        "session_end_hour": 24,
        "use_session_filter": False,
        "session2_start_hour": 0,
        "session2_end_hour": 0,
        "use_session2": False,
        "adx_period": 14,
        "adx_min_value": 10,
        "use_adx_filter": False,
        "use_rsi_momentum": False,
        "use_trailing_stop": False,
        "breakeven_atr_multiplier": 1.0,
        "trailing_atr_multiplier": 1.5,
        "use_retest_filter": False,
        "retest_timeout_bars": 4,
        "use_candle_confirm": False,
    }
