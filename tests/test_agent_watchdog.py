import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mt5_bot.agent_watchdog import (
    JournalStatus,
    MT5Health,
    evaluate_health,
    format_report,
    should_agent_run,
    write_jsonl_report,
)


def test_evaluate_health_ok_when_mt5_permissions_and_journals_are_fresh():
    now = datetime(2026, 6, 30, 1, 0, tzinfo=timezone.utc)
    health = evaluate_health(
        mt5=MT5Health(
            connected=True,
            account_trade_allowed=True,
            account_trade_expert=True,
            terminal_trade_allowed=True,
            tradeapi_disabled=False,
            balance=3000.0,
            equity=3001.0,
            margin=0.0,
            open_positions=0,
        ),
        journals=[JournalStatus("USDCHF", now - timedelta(minutes=2), "skipped", "no_signal")],
        now=now,
        floor_equity=2900.0,
        stale_after_seconds=900,
    )

    assert health.level == "ok"
    assert health.reasons == []
    assert health.summary["equity"] == 3001.0


def test_evaluate_health_critical_when_terminal_blocks_trading():
    now = datetime(2026, 6, 30, 1, 0, tzinfo=timezone.utc)
    health = evaluate_health(
        mt5=MT5Health(
            connected=True,
            account_trade_allowed=True,
            account_trade_expert=True,
            terminal_trade_allowed=False,
            tradeapi_disabled=False,
            balance=3000.0,
            equity=3000.0,
            margin=0.0,
            open_positions=0,
        ),
        journals=[],
        now=now,
        floor_equity=2900.0,
        stale_after_seconds=900,
    )

    assert health.level == "critical"
    assert "terminal_trade_allowed_false" in health.reasons
    assert not should_agent_run(health)


def test_evaluate_health_warns_when_symbol_journal_is_stale():
    now = datetime(2026, 6, 30, 1, 0, tzinfo=timezone.utc)
    health = evaluate_health(
        mt5=MT5Health(
            connected=True,
            account_trade_allowed=True,
            account_trade_expert=True,
            terminal_trade_allowed=True,
            tradeapi_disabled=False,
            balance=3000.0,
            equity=3000.0,
            margin=0.0,
            open_positions=0,
        ),
        journals=[JournalStatus("GBPJPY", now - timedelta(minutes=31), "skipped", "no_signal")],
        now=now,
        floor_equity=2900.0,
        stale_after_seconds=900,
    )

    assert health.level == "warn"
    assert "journal_stale:GBPJPY" in health.reasons


def test_write_jsonl_report_appends_one_json_object(tmp_path: Path):
    now = datetime(2026, 6, 30, 1, 0, tzinfo=timezone.utc)
    report = evaluate_health(
        mt5=MT5Health(
            connected=True,
            account_trade_allowed=True,
            account_trade_expert=True,
            terminal_trade_allowed=True,
            tradeapi_disabled=False,
            balance=3000.0,
            equity=3000.0,
            margin=0.0,
            open_positions=0,
        ),
        journals=[],
        now=now,
        floor_equity=2900.0,
        stale_after_seconds=900,
    )

    output = tmp_path / "health.jsonl"
    write_jsonl_report(output, report)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["level"] == "ok"
    assert parsed["summary"]["balance"] == 3000.0


def test_format_report_is_ascii_safe():
    now = datetime(2026, 6, 30, 1, 0, tzinfo=timezone.utc)
    report = evaluate_health(
        mt5=MT5Health(
            connected=True,
            account_trade_allowed=True,
            account_trade_expert=True,
            terminal_trade_allowed=True,
            tradeapi_disabled=False,
            balance=3000.0,
            equity=3000.0,
            margin=0.0,
            open_positions=0,
        ),
        journals=[JournalStatus("USDCHF", now, "skipped", "no_signal")],
        now=now,
        floor_equity=2900.0,
    )

    text = format_report(report)

    text.encode("ascii")
    assert "[MT5 Agent Watchdog OK]" in text
    assert should_agent_run(report)
