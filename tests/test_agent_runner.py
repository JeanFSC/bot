from pathlib import Path

from mt5_bot.agent_runner import AgentMode, load_agent_config


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
