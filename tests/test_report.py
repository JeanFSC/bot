from types import SimpleNamespace

from mt5_bot.report import generate_report, generate_report_per_magic, _losing_streak_from_profits
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


def _deal(ticket, profit, magic):
    d = SimpleNamespace(
        ticket=ticket, order=ticket+100, symbol="EURUSD", volume=0.1,
        price=1.1010, profit=profit, commission=0.0, swap=0.0, magic=magic,
        comment="", type=None, entry=None, time=None,
    )
    d._asdict = lambda: d.__dict__
    return d


def test_report_per_magic_isolates_bots(tmp_path):
    db_path = tmp_path / "trades.sqlite"
    storage = BotStorage(db_path)
    storage.record_account(SimpleNamespace(_asdict=lambda: {"balance": 10_000, "equity": 10_000, "margin": 0, "margin_free": 10_000}))
    # Magic 1: 3 wins of 100 each
    # Magic 2: 1 loss of -200
    storage.record_deals([
        _deal(1, 100.0, magic=1),
        _deal(2, 100.0, magic=1),
        _deal(3, 100.0, magic=1),
        _deal(4, -200.0, magic=2),
        _deal(5, -200.0, magic=2),
    ])
    storage.close()

    r1 = generate_report_per_magic(db_path, magic=1)
    r2 = generate_report_per_magic(db_path, magic=2)

    assert r1["trade_count"] == 3
    assert r1["wins"] == 3
    assert r1["profit_factor"] is None  # no losses → None
    assert r1["win_rate_pct"] == 100.0

    assert r2["trade_count"] == 2
    assert r2["wins"] == 0
    assert r2["profit_factor"] == 0.0 or r2["profit_factor"] is None  # no wins
    assert r2["win_rate_pct"] == 0.0


def test_max_losing_streak():
    assert _losing_streak_from_profits([]) == 0
    assert _losing_streak_from_profits([1.0, -1.0, -1.0, 1.0, -1.0]) == 2
    assert _losing_streak_from_profits([-1.0, -1.0, -1.0]) == 3
    assert _losing_streak_from_profits([1.0, 1.0]) == 0
    assert _losing_streak_from_profits([-1.0, 1.0, -1.0, -1.0, -1.0, 1.0]) == 3


def test_report_per_magic_streak(tmp_path):
    db_path = tmp_path / "streak.sqlite"
    storage = BotStorage(db_path)
    storage.record_account(SimpleNamespace(_asdict=lambda: {"balance": 10_000, "equity": 10_000, "margin": 0, "margin_free": 10_000}))
    storage.record_deals([
        _deal(1, -50.0, magic=99),
        _deal(2, -50.0, magic=99),
        _deal(3, -50.0, magic=99),
        _deal(4, 100.0, magic=99),
        _deal(5, -50.0, magic=99),
    ])
    storage.close()

    r = generate_report_per_magic(db_path, magic=99)
    assert r["max_losing_streak"] == 3
