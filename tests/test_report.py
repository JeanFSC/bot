from types import SimpleNamespace

from mt5_bot.report import generate_report
from mt5_bot.storage import BotStorage


def test_report_calculates_trade_quality_metrics(tmp_path):
    db_path = tmp_path / "trades.sqlite"
    storage = BotStorage(db_path)
    storage.record_account(SimpleNamespace(_asdict=lambda: {"balance": 10_000, "equity": 10_000, "margin": 0, "margin_free": 10_000}))
    storage.record_account(SimpleNamespace(_asdict=lambda: {"balance": 10_070, "equity": 10_040, "margin": 0, "margin_free": 10_040}))
    storage.record_market_metrics("EURUSD", 1.1000, 1.1001, 1.0)
    storage.record_order_result(
        {"symbol": "EURUSD", "type": 0, "price": 1.1000, "volume": 0.1},
        SimpleNamespace(_asdict=lambda: {"retcode": 10009, "comment": "Done", "price": 1.1002}),
    )
    storage.record_deals(
        [
            SimpleNamespace(_asdict=lambda: {"ticket": 1, "order": 10, "symbol": "EURUSD", "volume": 0.1, "price": 1.1010, "profit": 120.0, "commission": 0.0, "swap": 0.0, "magic": 260430, "comment": "win"}),
            SimpleNamespace(_asdict=lambda: {"ticket": 2, "order": 11, "symbol": "EURUSD", "volume": 0.1, "price": 1.0990, "profit": -50.0, "commission": 0.0, "swap": 0.0, "magic": 260430, "comment": "loss"}),
        ]
    )
    storage.close()

    metrics = generate_report(db_path)

    assert metrics["profit_factor"] == 2.4
    assert metrics["win_rate_pct"] == 50.0
    assert metrics["expectancy"] == 35.0
    assert metrics["max_drawdown"] == 0.0
    assert metrics["avg_slippage_pips"] == 2.0
