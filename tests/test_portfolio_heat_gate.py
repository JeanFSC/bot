import json
from datetime import datetime, timezone

from mt5_bot.portfolio_heat_gate import portfolio_heat_gate_decision


def _write_report(path, payload):
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_portfolio_heat_gate_blocks_when_required_report_missing(tmp_path):
    decision = portfolio_heat_gate_decision(tmp_path / "missing.jsonl", required=True)

    assert decision.allow_new_entry is False
    assert decision.reason == "portfolio_heat_missing"
    assert decision.risk_multiplier == 0.0


def test_portfolio_heat_gate_allows_when_report_ok_and_fresh(tmp_path):
    path = tmp_path / "heat.jsonl"
    now = datetime(2026, 7, 2, 4, 0, tzinfo=timezone.utc)
    _write_report(path, {"created_at": now.isoformat(), "decision": "allow_new_entries"})

    decision = portfolio_heat_gate_decision(path, now=now)

    assert decision.allow_new_entry is True
    assert decision.reason == "portfolio_heat_ok"
    assert decision.risk_multiplier == 1.0


def test_portfolio_heat_gate_blocks_on_heat_block(tmp_path):
    path = tmp_path / "heat.jsonl"
    now = datetime(2026, 7, 2, 4, 0, tzinfo=timezone.utc)
    _write_report(path, {"created_at": now.isoformat(), "decision": "block_new_entries_recommended"})

    decision = portfolio_heat_gate_decision(path, now=now)

    assert decision.allow_new_entry is False
    assert decision.reason == "portfolio_heat_block"


def test_portfolio_heat_gate_reduces_on_heat_reduce(tmp_path):
    path = tmp_path / "heat.jsonl"
    now = datetime(2026, 7, 2, 4, 0, tzinfo=timezone.utc)
    _write_report(path, {"created_at": now.isoformat(), "decision": "reduce_or_wait_recommended"})

    decision = portfolio_heat_gate_decision(path, reduce_risk_multiplier=0.4, now=now)

    assert decision.allow_new_entry is True
    assert decision.reason == "portfolio_heat_reduce"
    assert decision.risk_multiplier == 0.4


def test_portfolio_heat_gate_blocks_when_required_report_stale(tmp_path):
    path = tmp_path / "heat.jsonl"
    now = datetime(2026, 7, 2, 4, 2, tzinfo=timezone.utc)
    _write_report(
        path,
        {"created_at": datetime(2026, 7, 2, 4, 0, tzinfo=timezone.utc).isoformat(), "decision": "allow_new_entries"},
    )

    decision = portfolio_heat_gate_decision(path, max_age_seconds=30, required=True, now=now)

    assert decision.allow_new_entry is False
    assert decision.reason == "portfolio_heat_stale"
    assert decision.stale is True
