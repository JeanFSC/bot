from types import SimpleNamespace

import pytest

from mt5_bot.config import BotConfig, ExecutionConfig
from mt5_bot.portfolio_heat import build_config_map, build_heat_report


def _config(symbol: str, magic: int) -> BotConfig:
    return BotConfig(
        symbol=symbol,
        baseline_equity=3000.0,
        execution=ExecutionConfig(magic=magic, trade_enabled=False),
        max_total_margin_pct=35.0,
        max_portfolio_open_positions=10,
        max_same_currency_positions=6,
        max_daily_loss_pct=2.0,
    )


class FakeGateway:
    def order_calc_profit(self, order_type, symbol, volume, price_open, price_close):
        multiplier = 100_000.0 * volume
        if order_type == 0:
            return (price_close - price_open) * multiplier
        return (price_open - price_close) * multiplier


def test_build_heat_report_projects_owned_risk_to_sl_and_reward_to_tp():
    account = SimpleNamespace(equity=3000.0, margin=300.0)
    positions = [
        SimpleNamespace(
            ticket=1,
            symbol="EURUSD",
            magic=260001,
            type=0,
            volume=0.10,
            price_open=1.1000,
            sl=1.0980,
            tp=1.1040,
            profit=-2.0,
        ),
        SimpleNamespace(symbol="XAUUSD", magic=999999, profit=5.0),
    ]

    report = build_heat_report(FakeGateway(), account, positions, {("EURUSD", 260001): _config("EURUSD", 260001)})

    assert report.checked_positions == 2
    assert report.owned_positions == 1
    assert report.unknown_positions == 1
    assert round(report.risk_to_sl_usd, 2) == 20.00
    assert round(report.reward_to_tp_usd, 2) == 40.00
    assert report.currency_exposure == {"EUR": 1, "USD": 1}
    assert report.decision == "allow_new_entries"


def test_build_config_map_rejects_duplicate_symbol_magic():
    configs = [_config("EURUSD", 260001), _config("EURUSD", 260001)]

    with pytest.raises(ValueError, match="Duplicate portfolio owner config"):
        build_config_map(configs)


def test_build_heat_report_blocks_when_position_has_no_sl():
    account = SimpleNamespace(equity=3000.0, margin=100.0)
    positions = [
        SimpleNamespace(
            ticket=1,
            symbol="EURUSD",
            magic=260001,
            type=0,
            volume=0.10,
            price_open=1.1000,
            sl=0.0,
            tp=1.1040,
            profit=0.0,
        )
    ]

    report = build_heat_report(FakeGateway(), account, positions, {("EURUSD", 260001): _config("EURUSD", 260001)})

    assert report.decision == "block_new_entries_recommended"
    assert report.unprotected_positions == 1
    assert "unprotected_positions_1" in report.reasons


def test_build_heat_report_recommends_reduction_for_crowded_currency():
    account = SimpleNamespace(equity=3000.0, margin=100.0)
    positions = [
        SimpleNamespace(
            ticket=i,
            symbol=symbol,
            magic=260001 + i,
            type=0,
            volume=0.01,
            price_open=1.1000,
            sl=1.0990,
            tp=1.1020,
            profit=0.0,
        )
        for i, symbol in enumerate(["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF"], start=1)
    ]
    configs = {(position.symbol, position.magic): _config(position.symbol, position.magic) for position in positions}

    report = build_heat_report(FakeGateway(), account, positions, configs)

    assert report.decision == "reduce_or_wait_recommended"
    assert any(reason.startswith("crowded_currency_USD:6") for reason in report.reasons)
