from pathlib import Path
from types import SimpleNamespace

from mt5_bot import agent_runner
from mt5_bot.agent_runner import AgentMode, AgentRunnerConfig, load_agent_config


def test_load_agent_config_defaults(tmp_path: Path):
    cfg_path = tmp_path / "agent.yaml"
    cfg_path.write_text(
        "\n".join([
            "memory_db: data/test_agent_memory.sqlite",
            "configs:",
            "  - config/pro_gold.yaml",
        ]),
        encoding="utf-8",
    )

    config = load_agent_config(cfg_path)

    assert config.memory_db == Path("data/test_agent_memory.sqlite")
    assert config.configs == [Path("config/pro_gold.yaml")]
    assert config.mode is AgentMode.PAPER
    assert config.max_parallel_bots == 1
    assert config.allow_demo_orders is False


def test_load_agent_config_rejects_demo_orders_without_explicit_flag(tmp_path: Path):
    cfg_path = tmp_path / "agent.yaml"
    cfg_path.write_text(
        "\n".join([
            "mode: demo",
            "allow_demo_orders: false",
            "configs:",
            "  - config/pro_gold.yaml",
        ]),
        encoding="utf-8",
    )

    config = load_agent_config(cfg_path)

    assert config.mode is AgentMode.DEMO
    assert config.allow_demo_orders is False


def test_load_agent_config_prioritizes_live_positions_by_default(tmp_path: Path):
    cfg_path = tmp_path / "agent.yaml"
    cfg_path.write_text(
        "\n".join([
            "configs:",
            "  - config/pro_gold.yaml",
        ]),
        encoding="utf-8",
    )

    config = load_agent_config(cfg_path)

    assert config.prioritize_live_positions is True


def test_configs_prioritizing_live_positions_moves_open_symbols_first(monkeypatch):
    paths = [Path("config/a.yaml"), Path("config/b.yaml"), Path("config/c.yaml")]
    config = AgentRunnerConfig(configs=paths)
    loaded = {
        paths[0]: SimpleNamespace(symbol="EURUSD", execution=SimpleNamespace(magic=1)),
        paths[1]: SimpleNamespace(symbol="XAUUSD", execution=SimpleNamespace(magic=2)),
        paths[2]: SimpleNamespace(symbol="GBPUSD", execution=SimpleNamespace(magic=3)),
    }

    monkeypatch.setattr(agent_runner, "_active_position_keys", lambda: {("XAUUSD", 2)})
    monkeypatch.setattr(agent_runner, "load_config", lambda path: loaded[path])

    ordered = agent_runner._configs_prioritizing_live_positions(config)

    assert ordered == [paths[1], paths[0], paths[2]]


def test_configs_prioritizing_live_positions_can_be_disabled(monkeypatch):
    paths = [Path("config/a.yaml"), Path("config/b.yaml")]
    config = AgentRunnerConfig(configs=paths, prioritize_live_positions=False)

    monkeypatch.setattr(agent_runner, "_active_position_keys", lambda: {("XAUUSD", 2)})

    assert agent_runner._configs_prioritizing_live_positions(config) == paths
