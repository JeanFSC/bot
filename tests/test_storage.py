from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from mt5_bot.storage import BotStorage


def test_get_pnl_last_hour_includes_commission_and_swap(tmp_path):
    storage = BotStorage(tmp_path / "trades.sqlite")
    now = datetime.now(timezone.utc)
    storage.connection.execute(
        """
        INSERT INTO deals (
            ticket, created_at, order_id, symbol, deal_type, entry, volume,
            price, profit, commission, swap, magic, comment, raw_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            (now - timedelta(minutes=5)).isoformat(),
            10,
            "EURUSD",
            1,
            1,
            0.1,
            1.1000,
            -10.0,
            -2.5,
            -0.5,
            260430,
            "loss",
            "{}",
        ),
    )
    storage.connection.commit()

    assert storage.get_pnl_last_hour("EURUSD", 260430) == -13.0

    storage.close()


def test_storage_enables_wal_and_busy_timeout(tmp_path):
    storage = BotStorage(tmp_path / "trades.sqlite")

    journal_mode = storage.connection.execute("PRAGMA journal_mode").fetchone()[0]
    busy_timeout = storage.connection.execute("PRAGMA busy_timeout").fetchone()[0]

    assert journal_mode.lower() == "wal"
    assert busy_timeout == 30000

    storage.close()


def test_prune_position_metrics_archives_stale_rows(tmp_path):
    storage = BotStorage(tmp_path / "trades.sqlite")
    opened_at = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)
    position = SimpleNamespace(
        ticket=12345,
        symbol="GBPJPY",
        magic=260443,
        time=int(opened_at.timestamp()),
        type=1,
        volume=0.01,
        price_open=215.031,
        profit=0.25,
    )
    storage.record_position_metrics(position, current_price=215.006, current_pips=2.5)
    position.profit = -0.10
    storage.record_position_metrics(position, current_price=215.041, current_pips=-1.0)

    removed = storage.prune_position_metrics("GBPJPY", 260443, open_tickets=set())

    assert removed == 1
    assert storage.get_position_metrics(12345) is None
    archived = storage.connection.execute(
        """
        SELECT ticket, symbol, magic, mfe_pips, mae_pips, mfe_profit, mae_profit
        FROM position_metrics_history
        WHERE ticket = ?
        """,
        (12345,),
    ).fetchone()
    assert archived is not None
    assert archived["symbol"] == "GBPJPY"
    assert archived["magic"] == 260443
    assert archived["mfe_pips"] == 2.5
    assert archived["mae_pips"] == -1.0
    assert archived["mfe_profit"] == 0.25
    assert archived["mae_profit"] == -0.10

    storage.close()
