from types import SimpleNamespace

from mt5_bot.cli import _filter_history_deals_for_bot


def _deal(symbol: str, magic: int):
    return SimpleNamespace(symbol=symbol, magic=magic)


def test_history_deal_sync_keeps_only_matching_symbol_and_magic():
    deals = [
        _deal("XAUUSD", 260436),
        _deal("XAUUSD", 260440),
        _deal("EURUSD", 260436),
        _deal("XAUUSD", 0),
    ]

    filtered = _filter_history_deals_for_bot(deals, "XAUUSD", 260440)

    assert [d.magic for d in filtered] == [260440]


def test_history_deal_sync_excludes_zero_magic_same_symbol_deals():
    deals = [
        _deal("XAUUSD", 260436),
        _deal("XAUUSD", 0),
    ]

    filtered = _filter_history_deals_for_bot(deals, "XAUUSD", 260436)

    assert [d.magic for d in filtered] == [260436]
