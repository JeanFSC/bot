from __future__ import annotations

from collections import namedtuple
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from mt5_bot import mcp_server


class _ListLike:
    def tolist(self):
        return [1, 2, {"nested": 3}]


class _ScalarLike:
    def item(self):
        return 42


class _FakeMT5:
    ORDER_TYPE_BUY = 0
    COPY_TICKS_ALL = -1
    TRADE_ACTION_DEAL = 1
    _PRIVATE_CONST = "hidden"

    def __init__(self):
        self.calls: list[tuple[str, tuple, dict]] = []
        self.initialized_with = None
        self.login_args = None
        self.order_send_called = False

    def last_error(self):
        return (0, "ok")

    def account_info(self):
        Account = namedtuple("Account", ["login", "balance"])
        return Account(login=123456, balance=1000.5)

    def symbols_total(self):
        return 77

    def order_send(self, request):
        self.order_send_called = True
        self.calls.append(("order_send", (request,), {}))
        return SimpleNamespace(retcode=10009, comment="Done")

    def initialize(self, path=None):
        self.initialized_with = path
        return True

    def login(self, login, password=None, server=None):
        self.login_args = (login, password, server)
        return True

    def shutdown(self):
        self.calls.append(("shutdown", (), {}))
        return True

    def _private(self):  # pragma: no cover - must never be reachable through dispatcher
        raise AssertionError("private call should be blocked")


@pytest.fixture()
def fake_mt5(monkeypatch):
    fake = _FakeMT5()
    monkeypatch.setattr(mcp_server, "_MT5", fake)
    monkeypatch.delenv("MT5_MCP_ENABLE_TRADING", raising=False)
    return fake


def test_json_safe_serializes_mt5_namedtuples_and_array_like_values():
    Tick = namedtuple("Tick", ["time", "bid", "payload", "scalar"])
    value = Tick(
        time=datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc),
        bid=1.2345,
        payload=_ListLike(),
        scalar=_ScalarLike(),
    )

    result = mcp_server._json_safe(value)

    assert result == {
        "time": "2026-06-28T12:00:00+00:00",
        "bid": 1.2345,
        "payload": [1, 2, {"nested": 3}],
        "scalar": 42,
    }


def test_decode_expands_mt5_constants_and_explicit_datetimes(fake_mt5):
    result = mcp_server._decode(
        {
            "type": {"$mt5_const": "ORDER_TYPE_BUY"},
            "from_time": {"$datetime": "2026-06-28T00:00:00Z"},
            "nested": [{"$mt5_const": "COPY_TICKS_ALL"}],
        }
    )

    assert result["type"] == 0
    assert result["from_time"] == datetime(2026, 6, 28, tzinfo=timezone.utc)
    assert result["nested"] == [-1]


def test_list_api_returns_public_callables_and_constants_only(fake_mt5):
    result = mcp_server.mt5_list_api()

    assert "account_info" in result["callables"]
    assert "symbols_total" in result["callables"]
    assert "_private" not in result["callables"]
    assert result["constants"]["ORDER_TYPE_BUY"] == 0
    assert result["constants"]["COPY_TICKS_ALL"] == -1
    assert "_PRIVATE_CONST" not in result["constants"]


def test_mt5_call_dispatches_public_read_api_and_serializes_result(fake_mt5):
    result = mcp_server.mt5_call("account_info")

    assert result == {
        "success": True,
        "result": {"login": 123456, "balance": 1000.5},
        "last_error": [0, "ok"],
    }


def test_mt5_call_blocks_trading_api_by_default(fake_mt5):
    result = mcp_server.mt5_call("order_send", args=[{"action": {"$mt5_const": "TRADE_ACTION_DEAL"}}])

    assert result["success"] is False
    assert "blocked" in result["error"]
    assert fake_mt5.order_send_called is False


def test_mt5_call_allows_full_api_when_trading_is_explicitly_enabled(fake_mt5, monkeypatch):
    monkeypatch.setenv("MT5_MCP_ENABLE_TRADING", "1")

    result = mcp_server.mt5_call("order_send", args=[{"action": {"$mt5_const": "TRADE_ACTION_DEAL"}}])

    assert result["success"] is True
    assert result["result"] == {"retcode": 10009, "comment": "Done"}
    assert fake_mt5.calls == [("order_send", ({"action": 1},), {})]


def test_mt5_call_rejects_private_names(fake_mt5):
    result = mcp_server.mt5_call("_private")

    assert result["success"] is False
    assert "public" in result["error"]


def test_connect_from_env_initializes_and_logs_in_without_returning_password(fake_mt5, monkeypatch):
    monkeypatch.setenv("MT5_TERMINAL_PATH", "C:/Program Files/MetaTrader 5/terminal64.exe")
    monkeypatch.setenv("MT5_LOGIN", "123456")
    monkeypatch.setenv("MT5_PASSWORD", "super-secret-demo-password")
    monkeypatch.setenv("MT5_SERVER", "MetaQuotes-Demo")

    result = mcp_server.mt5_connect_from_env()

    assert result["success"] is True
    assert result["initialized"] is True
    assert result["logged_in"] is True
    assert fake_mt5.initialized_with == "C:/Program Files/MetaTrader 5/terminal64.exe"
    assert fake_mt5.login_args == (123456, "super-secret-demo-password", "MetaQuotes-Demo")
    assert "super-secret-demo-password" not in repr(result)
