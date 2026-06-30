import sqlite3
from pathlib import Path

from mt5_bot.postmortem import analyze_trade_loss, sync_postmortems


def test_analyze_trade_loss_identifies_trend_conflict_and_corrective_action():
    analysis = analyze_trade_loss(
        symbol="GBPJPY",
        pnl=-1.25,
        context={
            "signal_type": "BUY",
            "trend_bias": "down",
            "adx": 31.0,
            "rsi": 72.0,
            "spread_pips": 2.5,
            "max_spread_pips": 3.0,
            "atr_pips": 4.2,
            "session": "session_ny",
        },
    )

    assert analysis["severity"] == "low"
    assert "trend_conflict" in analysis["causes"]
    assert "overbought_buy" in analysis["causes"]
    assert "block_or_reduce_trend_conflict_setup" in analysis["actions"]


def test_sync_postmortems_is_idempotent_and_only_records_losses(tmp_path: Path):
    db = tmp_path / "bot.sqlite"
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE deals (
            ticket INTEGER PRIMARY KEY,
            created_at TEXT NOT NULL,
            symbol TEXT,
            deal_type INTEGER,
            entry INTEGER,
            profit REAL,
            commission REAL,
            swap REAL,
            magic INTEGER,
            comment TEXT,
            raw_json TEXT NOT NULL
        );
        CREATE TABLE trade_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            symbol TEXT NOT NULL,
            magic INTEGER,
            signal_type TEXT NOT NULL,
            signal_reason TEXT NOT NULL,
            decision TEXT NOT NULL,
            execution_status TEXT,
            execution_reason TEXT,
            risk_pct REAL,
            risk_multiplier REAL,
            portfolio_reason TEXT,
            rr REAL,
            context_json TEXT NOT NULL
        );
        INSERT INTO trade_journal VALUES (
            1, '2026-06-30T01:00:00+00:00', 'GBPJPY', 260443,
            'BUY', 'ema_cross', 'ALLOW', 'sent', 'retcode_10009',
            0.05, 1.0, NULL, 1.5,
            '{"trend_bias":"down","adx":31,"rsi":72,"spread_pips":2.5,"max_spread_pips":3,"atr_pips":4.2}'
        );
        INSERT INTO deals VALUES (
            101, '2026-06-30T01:05:00+00:00', 'GBPJPY', 0, 1,
            -1.25, 0.0, 0.0, 260443, 'close', '{}'
        );
        INSERT INTO deals VALUES (
            102, '2026-06-30T01:06:00+00:00', 'GBPJPY', 0, 1,
            2.00, 0.0, 0.0, 260443, 'close', '{}'
        );
        """
    )
    con.commit(); con.close()

    first = sync_postmortems(db)
    second = sync_postmortems(db)

    assert first == 1
    assert second == 0
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT source_deal_ticket, symbol, pnl, causes_json, actions_json FROM trade_postmortems").fetchall()
    con.close()
    assert len(rows) == 1
    assert rows[0]["source_deal_ticket"] == 101
    assert rows[0]["symbol"] == "GBPJPY"
    assert rows[0]["pnl"] == -1.25
    assert "trend_conflict" in rows[0]["causes_json"]
    assert "block_or_reduce_trend_conflict_setup" in rows[0]["actions_json"]
