"""Tests for performance.py — score formula and suggestions."""
from __future__ import annotations

import pytest
from mt5_bot.performance import PerformanceMetrics, compute_score, combine_scores, suggestions


def _perfect() -> PerformanceMetrics:
    return PerformanceMetrics(
        trades=100, wins=70, losses=30,
        profit_factor=3.0, win_rate_pct=70.0,
        expectancy_pips=25.0, max_drawdown_pct=1.0,
        max_losing_streak=2, sharpe=2.5, sl_pips=20.0,
    )


def _worst() -> PerformanceMetrics:
    return PerformanceMetrics(
        trades=100, wins=30, losses=70,
        profit_factor=0.5, win_rate_pct=30.0,
        expectancy_pips=-15.0, max_drawdown_pct=20.0,
        max_losing_streak=10, sharpe=-1.0, sl_pips=20.0,
    )


def test_score_perfect_bot():
    score = compute_score(_perfect())
    assert score >= 9.5, f"Perfect bot score {score} < 9.5"


def test_score_worst_bot():
    score = compute_score(_worst())
    assert score <= 1.0, f"Worst bot score {score} > 1.0"


def test_score_zero_below_10_trades():
    m = _perfect()
    m.trades = 5
    assert compute_score(m) == 0.0


def test_pf_threshold_boundaries():
    # PF=1.0 → pf_score=0
    m = PerformanceMetrics(
        trades=50, wins=25, losses=25,
        profit_factor=1.0, win_rate_pct=50.0,
        expectancy_pips=10.0, max_drawdown_pct=3.0,
        max_losing_streak=3, sharpe=1.0, sl_pips=20.0,
    )
    score_at_1 = compute_score(m)
    m2 = PerformanceMetrics(**{**m.__dict__, "profit_factor": 2.5})
    score_at_25 = compute_score(m2)
    assert score_at_25 > score_at_1


def test_drawdown_threshold():
    # DD=0% → dd_score=1; DD=10% → dd_score=0
    base = dict(
        trades=50, wins=30, losses=20,
        profit_factor=2.0, win_rate_pct=60.0,
        expectancy_pips=15.0, max_losing_streak=2, sharpe=1.5, sl_pips=20.0,
    )
    low_dd = compute_score(PerformanceMetrics(**base, max_drawdown_pct=0.0))
    high_dd = compute_score(PerformanceMetrics(**base, max_drawdown_pct=10.0))
    assert low_dd > high_dd
    # At 10%+ DD, dd_score=0 → should lose exactly 2.5 points vs 0% DD
    assert abs((low_dd - high_dd) - 2.5) < 0.01


def test_combine_scores_no_live():
    bt = _perfect()
    score = combine_scores(bt, live=None)
    assert score == compute_score(bt)


def test_combine_scores_live_too_few_trades():
    bt = _perfect()
    live = PerformanceMetrics(
        trades=10, wins=7, losses=3,
        profit_factor=2.0, win_rate_pct=70.0,
        expectancy_pips=20.0, max_drawdown_pct=2.0,
        max_losing_streak=2, sharpe=2.0, sl_pips=20.0,
    )
    score = combine_scores(bt, live=live)
    # <30 live trades → 100% backtest
    assert score == compute_score(bt)


def test_combine_scores_with_live():
    bt = _perfect()
    live = PerformanceMetrics(
        trades=50, wins=40, losses=10,
        profit_factor=2.8, win_rate_pct=80.0,
        expectancy_pips=22.0, max_drawdown_pct=1.5,
        max_losing_streak=2, sharpe=2.2, sl_pips=20.0,
    )
    combined = combine_scores(bt, live=live, live_weight=0.4)
    expected = round(0.4 * compute_score(live) + 0.6 * compute_score(bt), 2)
    assert abs(combined - expected) < 0.01


def test_suggestions_dd_too_high():
    m = PerformanceMetrics(
        trades=50, wins=25, losses=25,
        profit_factor=1.8, win_rate_pct=50.0,
        expectancy_pips=10.0, max_drawdown_pct=7.0,
        max_losing_streak=3, sharpe=1.0, sl_pips=20.0,
    )
    hints = suggestions(m)
    assert any("DD" in h for h in hints)


def test_suggestions_pf_low():
    m = PerformanceMetrics(
        trades=50, wins=20, losses=30,
        profit_factor=1.2, win_rate_pct=40.0,
        expectancy_pips=5.0, max_drawdown_pct=3.0,
        max_losing_streak=3, sharpe=0.5, sl_pips=20.0,
    )
    hints = suggestions(m)
    assert any("PF" in h for h in hints)


def test_suggestions_streak():
    m = PerformanceMetrics(
        trades=50, wins=30, losses=20,
        profit_factor=2.0, win_rate_pct=60.0,
        expectancy_pips=15.0, max_drawdown_pct=2.0,
        max_losing_streak=5, sharpe=1.5, sl_pips=20.0,
    )
    hints = suggestions(m)
    assert any("Streak" in h or "streak" in h.lower() for h in hints)


def test_suggestions_slippage():
    m = _perfect()
    hints = suggestions(m, slippage_pips=1.5)
    assert any("Slippage" in h or "slippage" in h.lower() for h in hints)


def test_suggestions_clean_bot():
    m = _perfect()
    hints = suggestions(m, slippage_pips=0.3)
    assert len(hints) == 0
