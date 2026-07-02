from pathlib import Path
from types import SimpleNamespace

from mt5_bot import live_position_supervisor as supervisor
from mt5_bot.config import BotConfig, ExecutionConfig, RiskConfig


def _config(symbol: str, magic: int) -> BotConfig:
    return BotConfig(
        symbol=symbol,
        baseline_equity=3000.0,
        database_path=Path(f"data/test_{symbol.lower()}.sqlite"),
        execution=ExecutionConfig(magic=magic, trade_enabled=False),
        risk=RiskConfig(mode="fixed_lot", fixed_lot=0.01, risk_pct=0.1, sl_pips=10, tp_pips=20),
    )


def test_load_config_map_enables_trade_actions_only_when_requested(monkeypatch):
    path = Path("config/pro_test.yaml")
    monkeypatch.setattr(supervisor, "load_config", lambda p: _config("EURUSD", 260001))

    dry = supervisor._load_config_map([path], allow_trade_actions=False)
    live = supervisor._load_config_map([path], allow_trade_actions=True)

    assert dry[("EURUSD", 260001)].execution.trade_enabled is False
    assert live[("EURUSD", 260001)].execution.trade_enabled is True


def test_run_once_manages_only_owned_open_position(monkeypatch):
    cfg = _config("EURUSD", 260001)
    agent_config = SimpleNamespace(configs=[Path("config/pro_test.yaml")])
    calls = []

    class FakeGateway:
        def positions_get(self, symbol=None):
            if symbol:
                return []
            return [
                SimpleNamespace(symbol="EURUSD", magic=260001),
                SimpleNamespace(symbol="XAUUSD", magic=999999),
            ]

    monkeypatch.setattr(supervisor, "load_agent_config", lambda path: agent_config)
    monkeypatch.setattr(supervisor, "_load_config_map", lambda paths, allow_trade_actions: {("EURUSD", 260001): cfg})
    monkeypatch.setattr(
        supervisor,
        "_manage_config_positions",
        lambda gateway, config: calls.append((config.symbol, config.execution.magic)) or [
            supervisor.SupervisorAction(config.symbol, config.execution.magic, "telemetry", "position_metrics_1")
        ],
    )

    report = supervisor.run_once("config/autonomous_agent.yaml", gateway=FakeGateway())

    assert calls == [("EURUSD", 260001)]
    assert report.checked_positions == 2
    assert report.managed_positions == 1
    assert report.unknown_positions == 1
    assert report.actions[0].reason == "position_metrics_1"
