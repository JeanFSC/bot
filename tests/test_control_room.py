import json
from datetime import datetime, timezone

from mt5_bot.control_room import build_snapshot, read_latest_jsonl, render_summary


def test_read_latest_jsonl_returns_last_payload(tmp_path):
    path = tmp_path / "sample.jsonl"
    path.write_text('{"a": 1}\n{"a": 2}\n', encoding="utf-8")

    assert read_latest_jsonl(path) == {"a": 2}


def test_build_snapshot_ok_from_report_files(monkeypatch, tmp_path):
    supervisor = tmp_path / "supervisor.jsonl"
    heat = tmp_path / "heat.jsonl"
    watchdog = tmp_path / "watchdog.jsonl"
    supervisor.write_text(json.dumps({"managed_positions": 1, "unknown_positions": 0, "actions": []}) + "\n", encoding="utf-8")
    heat.write_text(
        json.dumps({
            "checked_positions": 1,
            "owned_positions": 1,
            "unknown_positions": 0,
            "unprotected_positions": 0,
            "decision": "allow_new_entries",
            "equity": 3000.0,
            "floating_pnl": 1.0,
            "risk_to_sl_usd": 5.0,
            "risk_to_sl_pct": 0.17,
        }) + "\n",
        encoding="utf-8",
    )
    watchdog.write_text(json.dumps({"level": "ok"}) + "\n", encoding="utf-8")
    monkeypatch.setattr("mt5_bot.control_room.audit_duplicate_trades", lambda: {"ok": True})

    snapshot = build_snapshot(
        supervisor_path=supervisor,
        heat_path=heat,
        watchdog_path=watchdog,
        now=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    assert snapshot.level == "ok"
    assert snapshot.reasons == ["ok"]
    assert "CONTROL_ROOM OK" in render_summary(snapshot)


def test_build_snapshot_warns_on_unprotected_positions(monkeypatch, tmp_path):
    supervisor = tmp_path / "supervisor.jsonl"
    heat = tmp_path / "heat.jsonl"
    supervisor.write_text(json.dumps({"managed_positions": 1, "unknown_positions": 0, "actions": []}) + "\n", encoding="utf-8")
    heat.write_text(json.dumps({"unprotected_positions": 1, "decision": "allow_new_entries"}) + "\n", encoding="utf-8")
    monkeypatch.setattr("mt5_bot.control_room.audit_duplicate_trades", lambda: {"ok": True})

    snapshot = build_snapshot(supervisor_path=supervisor, heat_path=heat, watchdog_path=tmp_path / "missing.jsonl")

    assert snapshot.level == "warn"
    assert "unprotected_positions_1" in snapshot.reasons
