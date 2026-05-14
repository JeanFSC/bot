from types import SimpleNamespace

from mt5_bot.portfolio_guard import portfolio_guard_decision, score_portfolio_overlap, symbol_currencies


def test_symbol_currencies_for_fx_and_gold():
    assert symbol_currencies("EURUSD") == {"EUR", "USD"}
    assert symbol_currencies("USDJPY") == {"USD", "JPY"}
    assert symbol_currencies("XAUUSD") == {"XAU", "USD"}


def test_portfolio_guard_blocks_excessive_margin_only_for_new_entries():
    config = SimpleNamespace(
        symbol="USDJPY",
        max_total_margin_pct=85.0,
        max_portfolio_open_positions=3,
        max_same_currency_positions=2,
    )
    account = SimpleNamespace(equity=100_000, margin=90_000)

    decision = portfolio_guard_decision(config, account, [])

    assert decision.allow_new_entry is False
    assert decision.reason.startswith("portfolio_margin_")


def test_portfolio_guard_allows_aggressive_but_not_crowded_account():
    config = SimpleNamespace(
        symbol="USDJPY",
        max_total_margin_pct=85.0,
        max_portfolio_open_positions=3,
        max_same_currency_positions=3,
    )
    account = SimpleNamespace(equity=100_000, margin=48_000)
    positions = [SimpleNamespace(symbol="USDJPY")]

    decision = portfolio_guard_decision(config, account, positions)

    assert decision.allow_new_entry is True
    assert decision.margin_pct == 48.0


def test_portfolio_guard_blocks_same_currency_crowding():
    config = SimpleNamespace(
        symbol="GBPUSD",
        max_total_margin_pct=85.0,
        max_portfolio_open_positions=5,
        max_same_currency_positions=2,
    )
    account = SimpleNamespace(equity=100_000, margin=20_000)
    positions = [SimpleNamespace(symbol="EURUSD"), SimpleNamespace(symbol="USDJPY")]

    decision = portfolio_guard_decision(config, account, positions)

    assert decision.allow_new_entry is False
    assert decision.reason == "same_currency_exposure_2"


def test_overlap_blocks_exact_symbol_duplicate_between_bots():
    config = SimpleNamespace(symbol="XAUUSD", max_same_currency_positions=3, max_exact_symbol_positions=1)
    positions = [SimpleNamespace(symbol="XAUUSD", type=0, magic=260436)]

    score = score_portfolio_overlap(config, positions, "BUY")

    assert score.allow_new_entry is False
    assert score.reason == "exact_symbol_overlap_1"
    assert score.risk_multiplier == 0.0


def test_overlap_descoring_reduces_same_direction_usd_theme():
    config = SimpleNamespace(symbol="GBPUSD", max_same_currency_positions=3, max_exact_symbol_positions=1)
    positions = [SimpleNamespace(symbol="EURUSD", type=0, magic=260433)]

    score = score_portfolio_overlap(config, positions, "BUY")

    assert score.allow_new_entry is True
    assert score.reason == "soft_overlap_descore"
    assert score.risk_multiplier == 0.5
    assert score.same_direction_theme_positions == 1
