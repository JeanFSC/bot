from datetime import date
from types import SimpleNamespace

from mt5_bot.cli import (
    _connect_and_validate,
    _control_room_entry_block_reason,
    _new_daily_risk_state,
    _runtime_trading_block_reason,
    _should_stop_after_action,
    _trade_loop_owns_dynamic_management,
)


def test_new_daily_risk_state_starts_with_zero_trades():
    state = _new_daily_risk_state(date(2026, 6, 28), account_equity=100_000.0, persisted_start_equity=None)

    assert state.start_equity == 100_000.0
    assert state.current_equity == 100_000.0
    assert state.trades_count == 0


def test_stop_after_action_only_stops_after_real_or_dryrun_action():
    assert _should_stop_after_action(True, "sent")
    assert _should_stop_after_action(True, "dry_run")
    assert not _should_stop_after_action(True, "rejected")
    assert not _should_stop_after_action(True, "skipped")
    assert not _should_stop_after_action(False, "sent")


def test_connect_and_validate_initializes_terminal_with_credentials_before_login():
    class FakeGateway:
        mt5 = SimpleNamespace(ACCOUNT_TRADE_MODE_DEMO=1)

        def __init__(self):
            self.initialize_args = None
            self.login_args = None
            self.selected_symbol = None

        def initialize(self, terminal_path=None, **kwargs):
            self.initialize_args = (terminal_path, kwargs)

        def login(self, login, password, server):
            self.login_args = (login, password, server)

        def account_info(self):
            return SimpleNamespace(
                trade_allowed=True,
                trade_expert=True,
                trade_mode=1,
                server="MetaQuotes-Demo",
            )

        def terminal_info(self):
            return SimpleNamespace(trade_allowed=True, build=5000)

        def symbol_select(self, symbol):
            self.selected_symbol = symbol

    gateway = FakeGateway()
    config = SimpleNamespace(
        symbol="USDCHF",
        account=SimpleNamespace(
            terminal_path="C:/Program Files/MetaTrader 5/terminal64.exe",
            login=123456,
            password="secret-demo-password",
            server="MetaQuotes-Demo",
            demo_only=True,
        ),
    )

    _connect_and_validate(gateway, config)

    assert gateway.initialize_args == (
        "C:/Program Files/MetaTrader 5/terminal64.exe",
        {"login": 123456, "password": "secret-demo-password", "server": "MetaQuotes-Demo"},
    )
    assert gateway.login_args == (123456, "secret-demo-password", "MetaQuotes-Demo")
    assert gateway.selected_symbol == "USDCHF"


def test_runtime_trading_block_reason_detects_terminal_python_disabled():
    account = SimpleNamespace(trade_allowed=True, trade_expert=True)
    terminal = SimpleNamespace(connected=True, trade_allowed=True, tradeapi_disabled=True)

    assert _runtime_trading_block_reason(account, terminal) == "tradeapi_disabled_true"


def test_runtime_trading_block_reason_allows_clean_permissions():
    account = SimpleNamespace(trade_allowed=True, trade_expert=True)
    terminal = SimpleNamespace(connected=True, trade_allowed=True, tradeapi_disabled=False)

    assert _runtime_trading_block_reason(account, terminal) is None


def test_control_room_entry_block_reason_allows_ok(monkeypatch):
    monkeypatch.setattr(
        "mt5_bot.cli._build_control_room_snapshot",
        lambda: SimpleNamespace(
            created_at="2026-07-03T13:00:00+00:00",
            level="ok",
            reasons=["ok"],
        ),
    )

    reason, context = _control_room_entry_block_reason()

    assert reason is None
    assert context["level"] == "ok"


def test_control_room_entry_block_reason_blocks_warn(monkeypatch):
    monkeypatch.setattr(
        "mt5_bot.cli._build_control_room_snapshot",
        lambda: SimpleNamespace(
            created_at="2026-07-03T13:00:00+00:00",
            level="warn",
            reasons=["portfolio_heat_stale"],
        ),
    )

    reason, context = _control_room_entry_block_reason()

    assert reason == "control_room_not_ok"
    assert context["level"] == "warn"
    assert context["reasons"] == ["portfolio_heat_stale"]


def test_control_room_entry_block_reason_blocks_unavailable(monkeypatch):
    def raise_error():
        raise RuntimeError("broken snapshot")

    monkeypatch.setattr("mt5_bot.cli._build_control_room_snapshot", raise_error)

    reason, context = _control_room_entry_block_reason()

    assert reason == "control_room_unavailable"
    assert context["level"] == "critical"


def test_trade_loop_skips_dynamic_management_when_supervisor_owns_it():
    assert _trade_loop_owns_dynamic_management(SimpleNamespace(dynamic_management_owner="supervisor")) is False
    assert _trade_loop_owns_dynamic_management(SimpleNamespace(dynamic_management_owner="trade_loop")) is True
    assert _trade_loop_owns_dynamic_management(SimpleNamespace()) is True


def test_new_daily_risk_state_seeds_trades_count_from_persisted_value():
    """A restart mid-day must not silently reset the daily trade-count guardrail."""
    state = _new_daily_risk_state(
        date(2026, 6, 28), account_equity=100_000.0, persisted_start_equity=None,
        persisted_trades_count=7,
    )

    assert state.trades_count == 7


def test_sleep_and_manage_trailing_skips_winner_scaling_when_disallowed(monkeypatch):
    from mt5_bot import cli as cli_module
    from mt5_bot.strategy import Signal, SignalType, StrategyConfig

    fake_signal = Signal(
        type=SignalType.NONE, price=None, time=None, reason="test",
        fast_ema=None, slow_ema=None, rsi=None, atr=None,
        atr_pips=5.0, trend_bias=None, adx=25.0,
    )
    monkeypatch.setattr("mt5_bot.strategy.detect_signal", lambda *a, **k: fake_signal)

    calls = {"winner_scaling": 0, "trailing_stop": 0}

    class FakeExecutor:
        gateway = SimpleNamespace(copy_rates_from_pos=lambda *a, **k: object())

        def record_position_metrics(self):
            return []

        def manage_time_stops(self):
            return []

        def manage_no_favorable_excursion(self, atr_pips):
            return []

        def manage_winner_scaling(self, atr_pips, adx, spread):
            calls["winner_scaling"] += 1
            return []

        def manage_profit_lock(self, atr_pips):
            return []

        def manage_trailing_stops(self, atr_pips):
            calls["trailing_stop"] += 1
            return []

    config = SimpleNamespace(
        symbol="EURUSD",
        timeframe="M5",
        poll_seconds=0,
        dynamic_management_owner="trade_loop",
        strategy=StrategyConfig(use_trailing_stop=True),
        use_partial_close=False,
    )

    cli_module._sleep_and_manage_trailing(FakeExecutor(), config, current_spread=1.0, allow_winner_scaling=False)

    assert calls["winner_scaling"] == 0
    assert calls["trailing_stop"] == 1
