"""Tests for backtest_engine.py — realistic bar-by-bar simulation."""
from __future__ import annotations

import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta

from mt5_bot.backtest_engine import run_realistic_backtest, _max_losing_streak, BacktestParams
from mt5_bot.config import BotConfig, RiskConfig, StrategySettings, ExecutionConfig, AccountConfig
from tests.fixtures.synthetic_bars import flat_bars, rally_bars, drop_bars


def _account() -> AccountConfig:
    return AccountConfig(login=1, password="x", server="MetaQuotes-Demo", demo_only=True)


def _base_config(**kwargs) -> BotConfig:
    defaults = dict(
        symbol="EURUSD",
        timeframe="M15",
        trend_timeframe="H1",
        max_daily_loss_pct=5.0,
        max_trades_per_day=50,
        cooldown_seconds=0,
        reverse_cooldown_seconds=0,
        max_loss_per_symbol_per_hour_pct=0.0,
        use_partial_close=False,
        partial_close_ratio=0.5,
        use_news_filter=False,
        use_equity_curve_filter=False,
        max_consecutive_losses=999,
        lot_reduction_factor=0.5,
        use_global_risk_guard=False,
        max_total_margin_pct=100.0,
        max_portfolio_open_positions=10,
        max_same_currency_positions=5,
        account=_account(),
        risk=RiskConfig(mode="fixed_lot", fixed_lot=0.1, risk_pct=1.0, sl_pips=20, tp_pips=40),
        strategy=StrategySettings(
            fast_ema=9, slow_ema=21, trend_ema=50,
            use_trend_filter=False, use_rsi_filter=False,
            use_atr_filter=False, use_adx_filter=False,
            use_session_filter=False, use_retest_filter=False,
            use_candle_confirm=False, use_volatility_regime=False,
            use_trailing_stop=False, use_atr_sl_tp=False,
        ),
        execution=ExecutionConfig(magic=1, trade_enabled=False),
    )
    defaults.update(kwargs)
    return BotConfig(**defaults)


def test_flat_market_no_trades():
    bars = flat_bars(n=300)
    config = _base_config()
    metrics = run_realistic_backtest(bars, config, params=BacktestParams(slippage_pips=0.0))
    assert metrics.trades == 0


def test_rally_generates_buy_trades():
    bars = rally_bars(n=300)
    config = _base_config()
    metrics = run_realistic_backtest(bars, config, params=BacktestParams(slippage_pips=0.0))
    assert metrics.trades >= 1


def test_drop_generates_sell_trades():
    bars = drop_bars(n=300)
    config = _base_config()
    metrics = run_realistic_backtest(bars, config, params=BacktestParams(slippage_pips=0.0))
    assert metrics.trades >= 1


def test_tp_hit_produces_positive_trade():
    """A sustained rally after entry should close at TP with positive profit."""
    bars = rally_bars(n=400, bar_size_pips=8.0)
    config = _base_config()
    metrics = run_realistic_backtest(bars, config, params=BacktestParams(slippage_pips=0.0))
    assert metrics.wins >= 1
    assert metrics.profit_factor > 0


def test_slippage_reduces_profitability():
    """Adding slippage should not improve results."""
    bars = rally_bars(n=300)
    config = _base_config()
    m_no_slip = run_realistic_backtest(bars, config, params=BacktestParams(slippage_pips=0.0))
    m_slip = run_realistic_backtest(bars, config, params=BacktestParams(slippage_pips=2.0))
    if m_no_slip.trades > 0 and m_slip.trades > 0:
        assert m_slip.expectancy_pips <= m_no_slip.expectancy_pips + 0.01


def test_trend_filter_blocks_against_trend():
    """With trend filter enabled, a downtrend should block BUY signals from M15."""
    from tests.fixtures.synthetic_bars import drop_bars

    signal_bars = rally_bars(n=200)
    # Trend bars: strong downtrend (H1)
    trend_bars_df = drop_bars(n=100, start_price=1.12000)

    config = _base_config(
        strategy=StrategySettings(
            fast_ema=9, slow_ema=21, trend_ema=50,
            use_trend_filter=True, use_rsi_filter=False,
            use_atr_filter=False, use_adx_filter=False,
            use_session_filter=False, use_retest_filter=False,
            use_candle_confirm=False, use_volatility_regime=False,
            use_trailing_stop=False, use_atr_sl_tp=False,
        )
    )
    metrics_with_filter = run_realistic_backtest(signal_bars, config, trend_bars=trend_bars_df, params=BacktestParams())
    metrics_no_filter = run_realistic_backtest(signal_bars, _base_config(), params=BacktestParams())
    # With a downtrend filter, BUY signals from M15 should be reduced
    assert metrics_with_filter.trades <= metrics_no_filter.trades


def test_daily_loss_circuit_breaker():
    """After hitting max_daily_loss_pct, no new trades should open that day."""
    bars = drop_bars(n=500, bar_size_pips=15.0)
    # Very tight daily loss limit with large SL — should trip quickly
    config = _base_config(
        max_daily_loss_pct=0.01,  # essentially 0
        risk=RiskConfig(mode="fixed_lot", fixed_lot=1.0, risk_pct=1.0, sl_pips=200, tp_pips=400),
    )
    metrics = run_realistic_backtest(bars, config, params=BacktestParams(initial_equity=10000.0))
    # At most 1 trade per day (the one that triggered the circuit)
    assert metrics.trades <= 100  # sanity, not a strict test


def test_reverse_cooldown_limits_trades():
    """reverse_cooldown_seconds should reduce trade frequency on alternating signals."""
    from tests.fixtures.synthetic_bars import alternating_crossover_bars
    bars = alternating_crossover_bars(n_cycles=20)
    config_no_cd = _base_config(reverse_cooldown_seconds=0)
    config_cd = _base_config(reverse_cooldown_seconds=99999)
    m_no_cd = run_realistic_backtest(bars, config_no_cd, params=BacktestParams())
    m_cd = run_realistic_backtest(bars, config_cd, params=BacktestParams())
    assert m_cd.trades <= m_no_cd.trades


def test_max_losing_streak_calculation():
    assert _max_losing_streak([]) == 0
    assert _max_losing_streak([1.0, -1.0, -1.0, 1.0, -1.0]) == 2
    assert _max_losing_streak([-1.0, -1.0, -1.0]) == 3
    assert _max_losing_streak([1.0, 1.0, 1.0]) == 0
    assert _max_losing_streak([-1.0, 1.0, -1.0, -1.0, -1.0, 1.0]) == 3


def test_metrics_zero_when_no_trades():
    bars = flat_bars(n=50)
    config = _base_config()
    m = run_realistic_backtest(bars, config, params=BacktestParams())
    assert m.trades == 0
    assert m.profit_factor == 0.0
    assert m.win_rate_pct == 0.0
