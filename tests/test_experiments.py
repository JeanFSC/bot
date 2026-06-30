import json
from pathlib import Path

from mt5_bot.experiments import ExperimentLog


def test_experiment_log_creates_and_updates_experiment(tmp_path: Path):
    log = ExperimentLog(tmp_path / "experiments.jsonl")

    exp = log.start(
        name="risk_usdchf_005",
        hypothesis="Riesgo 0.05 reduce drawdown mientras aprende",
        changes={"risk_pct": 0.05, "symbols": ["USDCHF"]},
    )
    log.finish(exp["id"], outcome="keep", metrics={"net_pnl": 1.2, "trades": 5})

    events = log.read_all()
    assert events[0]["event"] == "start"
    assert events[0]["name"] == "risk_usdchf_005"
    assert events[1]["event"] == "finish"
    assert events[1]["outcome"] == "keep"
    assert events[1]["metrics"]["trades"] == 5


def test_experiment_log_can_render_markdown(tmp_path: Path):
    log = ExperimentLog(tmp_path / "experiments.jsonl")
    exp = log.start("spread_filter", "Menos spread = menos pérdidas", {"max_spread_pips": 2.0})
    log.note(exp["id"], "Primeras señales bloqueadas correctamente")

    text = log.render_markdown()

    assert "# Experiment Log" in text
    assert "spread_filter" in text
    assert "Primeras señales" in text
