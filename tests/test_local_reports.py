import sqlite3
from pathlib import Path

from mt5_bot.local_reports import collect_database_metrics, render_markdown_report, write_local_report


def _make_db(path: Path, symbol: str, profit: float):
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE deals (
            ticket INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL,
            symbol TEXT,
            entry INTEGER,
            profit REAL,
            commission REAL,
            swap REAL,
            magic INTEGER
        );
        CREATE TABLE trade_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            symbol TEXT NOT NULL,
            execution_status TEXT,
            execution_reason TEXT
        );
        CREATE TABLE trade_postmortems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_deal_ticket INTEGER NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            symbol TEXT NOT NULL,
            magic INTEGER,
            pnl REAL NOT NULL,
            severity TEXT NOT NULL,
            causes_json TEXT NOT NULL,
            actions_json TEXT NOT NULL,
            context_json TEXT NOT NULL,
            notes TEXT NOT NULL
        );
        CREATE TABLE account_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            balance REAL,
            equity REAL,
            margin REAL,
            margin_free REAL,
            raw_json TEXT NOT NULL
        );
        CREATE TABLE runtime_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            level TEXT NOT NULL,
            symbol TEXT,
            magic INTEGER,
            event_type TEXT NOT NULL,
            reason TEXT NOT NULL,
            context_json TEXT NOT NULL
        );
        """
    )
    con.execute("INSERT INTO deals VALUES (1, '2026-06-30T01:00:00+00:00', ?, 1, ?, 0, 0, 260443)", (symbol, profit))
    con.execute("INSERT INTO trade_journal (created_at, symbol, execution_status, execution_reason) VALUES ('2026-06-30T01:02:00+00:00', ?, 'skipped', 'no_signal')", (symbol,))
    con.execute("INSERT INTO account_snapshots (created_at, balance, equity, margin, margin_free, raw_json) VALUES ('2026-06-30T01:01:00+00:00', 3000, 2999, 0, 2999, '{}')")
    con.execute("INSERT INTO runtime_events (created_at, level, symbol, magic, event_type, reason, context_json) VALUES ('2026-06-30T01:02:30+00:00', 'info', ?, 260443, 'pretrade_block', 'spread_filter', '{}')", (symbol,))
    if profit < 0:
        con.execute("INSERT INTO trade_postmortems VALUES (1, 1, '2026-06-30T01:03:00+00:00', ?, 260443, ?, 'low', '[\"trend_conflict\"]', '[\"block_or_reduce_trend_conflict_setup\"]', '{}', 'loss note')", (symbol, profit))
    con.commit(); con.close()


def test_collect_database_metrics_aggregates_pnl_and_postmortems(tmp_path: Path):
    db = tmp_path / "gbpjpy.sqlite"
    _make_db(db, "GBPJPY", -1.5)

    metrics = collect_database_metrics([db])

    assert metrics["totals"]["closed_trades"] == 1
    assert metrics["totals"]["net_pnl"] == -1.5
    assert metrics["symbols"]["GBPJPY"]["losses"] == 1
    assert metrics["postmortems"][0]["causes"] == ["trend_conflict"]
    assert metrics["latest_account"]["equity"] == 2999.0
    assert metrics["top_runtime_events"][0] == ("spread_filter", 1)


def test_render_markdown_report_includes_symbols_and_actions(tmp_path: Path):
    db = tmp_path / "gbpjpy.sqlite"
    _make_db(db, "GBPJPY", -1.5)
    metrics = collect_database_metrics([db])

    text = render_markdown_report(metrics, title="Reporte local")

    assert "# Reporte local" in text
    assert "GBPJPY" in text
    assert "block_or_reduce_trend_conflict_setup" in text
    assert "Top runtime/pre-signal events" in text


def test_write_local_report_creates_json_and_markdown(tmp_path: Path):
    db = tmp_path / "gbpjpy.sqlite"
    _make_db(db, "GBPJPY", 2.0)
    out_dir = tmp_path / "reports"

    result = write_local_report([db], out_dir, name="hourly")

    assert result["json_path"].exists()
    assert result["markdown_path"].exists()
    assert "GBPJPY" in result["markdown_path"].read_text(encoding="utf-8")
