from datetime import datetime, timedelta, timezone

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
