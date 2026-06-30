import textwrap
from pathlib import Path

import pytest

from mt5_bot.config import load_config


def _minimal_config(baseline_line: str) -> str:
    return textwrap.dedent(
        f"""
        symbol: EURUSD
        timeframe: M5
        trend_timeframe: H1
        demo_only: true
        {baseline_line}
        risk:
          mode: fixed_lot
          fixed_lot: 0.01
          risk_pct: 0.05
          sl_pips: 10
          tp_pips: 20
        strategy: {{}}
        execution:
          magic: 260430
          trade_enabled: false
        """
    )


def test_config_requires_explicit_positive_baseline_equity(tmp_path):
    path = tmp_path / "bot.yaml"
    path.write_text(_minimal_config(""), encoding="utf-8")

    with pytest.raises(ValueError, match="baseline_equity"):
        load_config(path)


def test_config_accepts_explicit_positive_baseline_equity(tmp_path):
    path = tmp_path / "bot.yaml"
    path.write_text(_minimal_config("baseline_equity: 3000.0"), encoding="utf-8")

    config = load_config(path)

    assert config.baseline_equity == 3000.0


def test_all_bot_configs_load_with_explicit_baseline_equity():
    config_dir = Path(__file__).resolve().parents[1] / "config"
    configs = sorted(
        path
        for path in config_dir.glob("*.yaml")
        if path.name != "autonomous_agent.yaml"
    )

    assert configs
    for path in configs:
        config = load_config(path)
        assert config.baseline_equity > 0, path
