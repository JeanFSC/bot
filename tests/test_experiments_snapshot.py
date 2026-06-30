from pathlib import Path

from mt5_bot.experiments import ExperimentLog


def test_snapshot_configs_only_appends_when_fingerprint_changes(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("symbol: EURUSD\n", encoding="utf-8")
    log = ExperimentLog(tmp_path / "experiments.jsonl")

    first = log.snapshot_configs([cfg])
    second = log.snapshot_configs([cfg])
    cfg.write_text("symbol: GBPJPY\n", encoding="utf-8")
    third = log.snapshot_configs([cfg])

    assert first is not None
    assert second is None
    assert third is not None
    assert len([event for event in log.read_all() if event["event"] == "config_snapshot"]) == 2
