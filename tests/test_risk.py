from datetime import date
from types import SimpleNamespace

import pytest

from mt5_bot.config import RiskConfig
from mt5_bot.risk import DailyRiskState, calculate_volume, is_daily_loss_limit_hit, pip_size, prices_for_order
from mt5_bot.strategy import SignalType


def _symbol_info():
    return SimpleNamespace(
        digits=5,
        point=0.00001,
        trade_tick_value=1.0,
        trade_tick_size=0.00001,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
    )


def test_pip_size_for_five_digit_eurusd_symbol():
    assert pip_size(_symbol_info()) == pytest.approx(0.0001)


def test_prices_for_buy_order_apply_sl_and_tp_in_pips():
    prices = prices_for_order(SignalType.BUY, entry_price=1.10000, sl_pips=20, tp_pips=40, symbol_info=_symbol_info())

    assert prices.sl == pytest.approx(1.09800)
    assert prices.tp == pytest.approx(1.10400)


def test_fixed_lot_volume_is_normalized_to_symbol_step():
    config = RiskConfig(mode="fixed_lot", fixed_lot=0.105, risk_pct=0.25, sl_pips=20, tp_pips=40)

    assert calculate_volume(config, equity=10_000, symbol_info=_symbol_info()) == pytest.approx(0.10)


def test_percent_equity_volume_uses_stop_loss_distance():
    config = RiskConfig(mode="percent_equity", fixed_lot=0.1, risk_pct=0.25, sl_pips=20, tp_pips=40)

    assert calculate_volume(config, equity=10_000, symbol_info=_symbol_info()) == pytest.approx(0.12)


def test_daily_loss_limit_blocks_new_entries():
    state = DailyRiskState(day=date(2026, 1, 1), start_equity=10_000, current_equity=9_790, trades_count=1)

    assert is_daily_loss_limit_hit(state, max_daily_loss_pct=2.0)
