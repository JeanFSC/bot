from __future__ import annotations

from mt5_bot.mt5_gateway import MT5Gateway


class FakeMT5:
    def __init__(self, results, error):
        self.results = list(results)
        self.error = error
        self.initialize_calls: list[dict] = []

    def initialize(self, **kwargs):
        self.initialize_calls.append(kwargs)
        return self.results.pop(0)

    def last_error(self):
        return self.error


def test_initialize_retries_transient_authorization_failure(monkeypatch, tmp_path):
    fake = FakeMT5(
        [False, True],
        (-6, "Terminal: Authorization failed"),
    )
    monkeypatch.setitem(__import__("sys").modules, "MetaTrader5", fake)
    monkeypatch.setenv("MT5_INIT_LOCK_PATH", str(tmp_path / "mt5-init.lock"))
    monkeypatch.setenv("MT5_INIT_ATTEMPTS", "4")
    monkeypatch.setattr("mt5_bot.mt5_gateway.time.sleep", lambda seconds: None)
    monkeypatch.setattr("mt5_bot.mt5_gateway.random.uniform", lambda start, end: 0.0)

    gateway = MT5Gateway()
    gateway.initialize("C:/MT5/terminal64.exe", login=123, password="secret", server="Demo")

    assert fake.initialize_calls == [
        {"path": "C:/MT5/terminal64.exe", "login": 123, "password": "secret", "server": "Demo"},
        {"path": "C:/MT5/terminal64.exe", "login": 123, "password": "secret", "server": "Demo"},
    ]


def test_initialize_does_not_retry_non_transient_failure(monkeypatch, tmp_path):
    fake = FakeMT5(
        [False, False, False],
        (1, "Invalid account"),
    )
    monkeypatch.setitem(__import__("sys").modules, "MetaTrader5", fake)
    monkeypatch.setenv("MT5_INIT_LOCK_PATH", str(tmp_path / "mt5-init.lock"))
    monkeypatch.setenv("MT5_INIT_ATTEMPTS", "4")
    monkeypatch.setattr("mt5_bot.mt5_gateway.time.sleep", lambda seconds: None)

    gateway = MT5Gateway()

    try:
        gateway.initialize()
    except RuntimeError as exc:
        assert "Invalid account" in str(exc)
    else:
        raise AssertionError("initialize should fail")

    assert len(fake.initialize_calls) == 1
