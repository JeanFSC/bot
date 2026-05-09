from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class PerformanceMetrics:
    trades: int
    wins: int
    losses: int
    profit_factor: float
    win_rate_pct: float
    expectancy_pips: float
    max_drawdown_pct: float
    max_losing_streak: int
    sharpe: float
    sl_pips: float = 20.0
    source: str = "backtest"  # "backtest" | "live"


def compute_score(m: PerformanceMetrics) -> float:
    """Return a 0-10 score based on real performance metrics.

    Weights: PF 2.5, DD 2.5, WR 1.5, Expectancy 1.5, Streak 1.0, Sharpe 1.0
    """
    if m.trades < 10:
        return 0.0

    pf_score = _clamp((m.profit_factor - 1.0) / 1.5, 0.0, 1.0)
    dd_score = _clamp(1.0 - m.max_drawdown_pct / 10.0, 0.0, 1.0)
    wr_score = _clamp((m.win_rate_pct - 40.0) / 20.0, 0.0, 1.0)
    exp_score = _clamp(m.expectancy_pips / m.sl_pips, 0.0, 1.0) if m.sl_pips > 0 else 0.0
    streak_score = _clamp(1.0 - (m.max_losing_streak - 2) / 3.0, 0.0, 1.0)
    sharpe_score = _clamp(m.sharpe / 2.0, 0.0, 1.0)

    return round(
        2.5 * pf_score
        + 2.5 * dd_score
        + 1.5 * wr_score
        + 1.5 * exp_score
        + 1.0 * streak_score
        + 1.0 * sharpe_score,
        2,
    )


def combine_scores(
    backtest: PerformanceMetrics,
    live: Optional[PerformanceMetrics] = None,
    live_weight: float = 0.4,
) -> float:
    """Combine backtest and live scores.

    Falls back to 100% backtest if live has <30 trades (high variance).
    """
    bt_score = compute_score(backtest)
    if live is None or live.trades < 30:
        return bt_score
    lv_score = compute_score(live)
    return round(live_weight * lv_score + (1.0 - live_weight) * bt_score, 2)


def suggestions(m: PerformanceMetrics, slippage_pips: Optional[float] = None) -> list[str]:
    """Return actionable improvement suggestions based on the metrics."""
    hints: list[str] = []
    if m.max_drawdown_pct > 5:
        hints.append(
            f"DD {m.max_drawdown_pct:.1f}% > 5%: bajar risk_pct o reducir atr_sl_multiplier a 1.0"
        )
    if m.profit_factor < 1.5:
        hints.append(
            f"PF {m.profit_factor:.2f} < 1.5: subir adx_min_value en 3 pts o activar use_candle_confirm"
        )
    if m.win_rate_pct < 45 and m.expectancy_pips < 0:
        hints.append("WR bajo + expectancy negativa: revisar trend filter o MTF timeframe")
    if m.max_losing_streak >= 4:
        hints.append(
            f"Streak {m.max_losing_streak}: bajar lot_reduction_factor a 0.4"
        )
    if slippage_pips is not None and slippage_pips > 1.0:
        hints.append(
            f"Slippage {slippage_pips:.1f} pips: bajar deviation o usar filling_mode=IOC"
        )
    return hints
