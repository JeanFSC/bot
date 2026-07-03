from datetime import date
from types import SimpleNamespace

from mt5_bot.cli import (
    _connect_and_validate,
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


def test_trade_loop_skips_dynamic_management_when_supervisor_owns_it():
    assert _trade_loop_owns_dynamic_management(SimpleNamespace(dynamic_management_owner="supervisor")) is False
    assert _trade_loop_owns_dynamic_management(SimpleNamespace(dynamic_management_owner="trade_loop")) is True
    assert _trade_loop_owns_dynamic_management(SimpleNamespace()) is True
