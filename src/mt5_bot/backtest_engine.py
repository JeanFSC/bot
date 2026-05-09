"""
backtest_engine.py — Realistic bar-by-bar backtest simulator.

Features replicated from the live executor:
  • SL / TP resolved intra-bar (conservative: SL wins ties)
  • ATR-based dynamic SL/TP when use_atr_sl_tp=True
  • Multi-timeframe trend filter via detect_signal_mtf
  • Session filter
  • Slippage (fixed pips deducted from entry)
  • Partial close (partial_close_ratio of position closed at first TP touch)
  • Trailing stop (after breakeven_atr_multiplier×ATR favourable move)
  • Reverse cooldown between opposite-direction trades
  • Max consecutive losses guard (lot_reduction_factor applied but trade allowed)
  • Max daily loss circuit-breaker (no new trades after hit)
  • Hourly cap (max_loss_per_symbol_per_hour_pct)
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd

from mt5_bot.bars_loader import slice_trend_at
from mt5_bot.config import BotConfig
from mt5_bot.performance import PerformanceMetrics
from mt5_bot.report import _max_drawdown
from mt5_bot.strategy import (
    SignalType,
    StrategyConfig,
    _pip_size_for_symbol,
    detect_signal_mtf,
    ema,
    atr as atr_indicator,
)


# ── Pip-value table (USD per lot per pip) ───────────────────────────────────
# Approximate values; ±5% vs broker is expected.
_PIP_VALUE_PER_LOT: dict[str, float] = {
    "EURUSD": 10.0,
    "GBPUSD": 10.0,
    "AUDUSD": 10.0,
    "NZDUSD": 10.0,
    "USDCAD": 7.6,
    "USDCHF": 11.0,
    "USDJPY": 9.1,
    "GBPJPY": 9.1,
    "EURJPY": 9.1,
    "AUDJPY": 9.1,
    "NZDJPY": 9.1,
    "XAUUSD": 10.0,  # 1 pip = $0.01, 1 lot = 100oz → $1/pip per oz = $1 per 0.01 → 100 lots = $1000/pip; standard lot=100oz, 1 pip=$10
    "XAGUSD": 50.0,
}


def _pip_value(symbol: str) -> float:
    sym = symbol.upper().replace("/", "")
    return _PIP_VALUE_PER_LOT.get(sym, 10.0)


@dataclass
class BacktestParams:
    slippage_pips: float = 0.3
    initial_equity: float = 10_000.0
    lot_size: float = 0.1


@dataclass
class _ClosedTrade:
    entry_time: datetime
    exit_time: datetime
    direction: SignalType
    entry_price: float
    exit_price: float
    lot: float
    profit_usd: float
    profit_pips: float
    exit_reason: str  # "tp" | "sl" | "trailing" | "partial_tp" | "end_of_data"


@dataclass
class _OpenPosition:
    direction: SignalType
    entry_price: float
    lot: float
    sl: float
    tp: float
    entry_time: datetime
    initial_sl: float
    initial_tp: float
    atr_at_entry: Optional[float]
    partial_closed: bool = False
    trailing_active: bool = False
    trailing_sl: Optional[float] = None


def _resolve_sl_tp_intrabar(
    pos: _OpenPosition,
    bar_high: float,
    bar_low: float,
) -> Optional[str]:
    """Return exit reason if SL or TP was hit within the bar, else None.

    Conservative: if both SL and TP are hit in the same bar, SL wins.
    """
    if pos.direction is SignalType.BUY:
        sl_hit = bar_low <= pos.sl
        tp_hit = bar_high >= pos.tp
        if sl_hit:
            return "sl"
        if tp_hit:
            return "tp"
    else:  # SELL
        sl_hit = bar_high >= pos.sl
        tp_hit = bar_low <= pos.tp
        if sl_hit:
            return "sl"
        if tp_hit:
            return "tp"
    return None


def _trailing_update(
    pos: _OpenPosition,
    bar: pd.Series,
    config: StrategyConfig,
    pip: float,
    atr_val: Optional[float],
) -> _OpenPosition:
    """Advance trailing stop state. Returns updated position."""
    if not config.use_trailing_stop or atr_val is None:
        return pos

    breakeven_dist = config.breakeven_atr_multiplier * atr_val
    trailing_dist = config.trailing_atr_multiplier * atr_val

    if pos.direction is SignalType.BUY:
        move = bar["close"] - pos.entry_price
        if not pos.trailing_active and move >= breakeven_dist:
            pos = _replace_pos(pos, trailing_active=True, trailing_sl=pos.entry_price)
        if pos.trailing_active:
            new_sl = bar["close"] - trailing_dist
            current_sl = pos.trailing_sl if pos.trailing_sl is not None else pos.sl
            if new_sl > current_sl:
                pos = _replace_pos(pos, trailing_sl=new_sl, sl=new_sl)
    else:
        move = pos.entry_price - bar["close"]
        if not pos.trailing_active and move >= breakeven_dist:
            pos = _replace_pos(pos, trailing_active=True, trailing_sl=pos.entry_price)
        if pos.trailing_active:
            new_sl = bar["close"] + trailing_dist
            current_sl = pos.trailing_sl if pos.trailing_sl is not None else pos.sl
            if new_sl < current_sl:
                pos = _replace_pos(pos, trailing_sl=new_sl, sl=new_sl)
    return pos


def _replace_pos(pos: _OpenPosition, **kwargs) -> _OpenPosition:
    for k, v in kwargs.items():
        object.__setattr__(pos, k, v)
    return pos


def _profit_usd(direction: SignalType, entry: float, exit_price: float, lot: float, pip: float, pip_val: float) -> tuple[float, float]:
    if direction is SignalType.BUY:
        pips = (exit_price - entry) / pip
    else:
        pips = (entry - exit_price) / pip
    usd = pips * lot * pip_val
    return round(usd, 2), round(pips, 2)


def run_realistic_backtest(
    signal_bars: pd.DataFrame,
    config: BotConfig,
    trend_bars: Optional[pd.DataFrame] = None,
    params: Optional[BacktestParams] = None,
) -> PerformanceMetrics:
    """Run a bar-by-bar backtest and return PerformanceMetrics.

    signal_bars and trend_bars must have columns: time, open, high, low, close[, volume].
    time must be UTC-aware datetime.
    """
    if params is None:
        params = BacktestParams()

    strategy_config = StrategyConfig(**{
        f: getattr(config.strategy, f)
        for f in StrategyConfig.__dataclass_fields__  # type: ignore[attr-defined]
        if f in StrategyConfig.__dataclass_fields__  # type: ignore[attr-defined]
    })

    pip = _pip_size_for_symbol(config.symbol)
    pip_val = _pip_value(config.symbol)
    sl_pips_base = config.risk.sl_pips
    tp_pips_base = config.risk.tp_pips
    lot = params.lot_size

    closed_trades: list[_ClosedTrade] = []
    equity = params.initial_equity
    equity_curve: list[float] = [equity]
    open_pos: Optional[_OpenPosition] = None

    last_trade_time: Optional[datetime] = None
    last_trade_dir: Optional[SignalType] = None
    consecutive_losses: int = 0
    daily_loss_start_equity: float = equity
    current_trade_date: Optional[datetime] = None
    daily_trades: int = 0
    hourly_loss_tracker: list[tuple[datetime, float]] = []  # (time, loss_usd)

    min_bars = strategy_config.slow_ema + 5

    for i in range(min_bars, len(signal_bars)):
        bar = signal_bars.iloc[i]
        bar_time: datetime = bar["time"].to_pydatetime() if hasattr(bar["time"], "to_pydatetime") else bar["time"]
        if bar_time.tzinfo is None:
            bar_time = bar_time.replace(tzinfo=timezone.utc)

        # ── Daily reset ──────────────────────────────────────────────────────
        trade_date = bar_time.date()
        if current_trade_date != trade_date:
            current_trade_date = trade_date
            daily_loss_start_equity = equity
            daily_trades = 0

        # ── Manage open position ─────────────────────────────────────────────
        if open_pos is not None:
            # Trailing stop update using previous bar's ATR
            prev_bars = signal_bars.iloc[: i + 1]
            atr_series = atr_indicator(prev_bars, strategy_config.atr_period)
            atr_val = float(atr_series.iloc[-1]) if not pd.isna(atr_series.iloc[-1]) else None
            open_pos = _trailing_update(open_pos, bar, strategy_config, pip, atr_val)

            exit_reason = _resolve_sl_tp_intrabar(open_pos, float(bar["high"]), float(bar["low"]))

            if exit_reason == "tp":
                exit_px = open_pos.tp
                # Partial close: close partial_close_ratio at TP, keep rest
                if config.use_partial_close and not open_pos.partial_closed:
                    partial_lot = round(open_pos.lot * config.partial_close_ratio, 2)
                    p_usd, p_pips = _profit_usd(open_pos.direction, open_pos.entry_price, exit_px, partial_lot, pip, pip_val)
                    closed_trades.append(_ClosedTrade(
                        entry_time=open_pos.entry_time, exit_time=bar_time,
                        direction=open_pos.direction, entry_price=open_pos.entry_price,
                        exit_price=exit_px, lot=partial_lot,
                        profit_usd=p_usd, profit_pips=p_pips, exit_reason="partial_tp",
                    ))
                    equity += p_usd
                    remaining_lot = round(open_pos.lot - partial_lot, 2)
                    # Tighten SL to entry (breakeven) after partial close
                    new_sl = open_pos.entry_price
                    new_tp = open_pos.tp + (open_pos.tp - open_pos.entry_price)
                    open_pos = _OpenPosition(
                        direction=open_pos.direction, entry_price=open_pos.entry_price,
                        lot=remaining_lot, sl=new_sl, tp=new_tp,
                        entry_time=open_pos.entry_time, initial_sl=open_pos.initial_sl,
                        initial_tp=open_pos.initial_tp, atr_at_entry=open_pos.atr_at_entry,
                        partial_closed=True, trailing_active=open_pos.trailing_active,
                        trailing_sl=open_pos.trailing_sl,
                    )
                    equity_curve.append(equity)
                    continue
                else:
                    p_usd, p_pips = _profit_usd(open_pos.direction, open_pos.entry_price, exit_px, open_pos.lot, pip, pip_val)
                    consecutive_losses = 0

            elif exit_reason == "sl":
                exit_px = open_pos.sl
                p_usd, p_pips = _profit_usd(open_pos.direction, open_pos.entry_price, exit_px, open_pos.lot, pip, pip_val)
                consecutive_losses += 1
                hourly_loss_tracker.append((bar_time, p_usd))

            elif open_pos.trailing_active:
                # Check trailing SL hit
                if open_pos.trailing_sl is not None:
                    ts_hit = (
                        (open_pos.direction is SignalType.BUY and float(bar["low"]) <= open_pos.trailing_sl)
                        or (open_pos.direction is SignalType.SELL and float(bar["high"]) >= open_pos.trailing_sl)
                    )
                    if ts_hit:
                        exit_px = open_pos.trailing_sl
                        p_usd, p_pips = _profit_usd(open_pos.direction, open_pos.entry_price, exit_px, open_pos.lot, pip, pip_val)
                        exit_reason = "trailing"
                        if p_usd < 0:
                            consecutive_losses += 1
                            hourly_loss_tracker.append((bar_time, p_usd))
                        else:
                            consecutive_losses = 0
                        closed_trades.append(_ClosedTrade(
                            entry_time=open_pos.entry_time, exit_time=bar_time,
                            direction=open_pos.direction, entry_price=open_pos.entry_price,
                            exit_price=exit_px, lot=open_pos.lot,
                            profit_usd=p_usd, profit_pips=p_pips, exit_reason=exit_reason,
                        ))
                        equity += p_usd
                        equity_curve.append(equity)
                        last_trade_time = bar_time
                        last_trade_dir = open_pos.direction
                        open_pos = None
                        continue

            if exit_reason in ("tp", "sl"):
                closed_trades.append(_ClosedTrade(
                    entry_time=open_pos.entry_time, exit_time=bar_time,
                    direction=open_pos.direction, entry_price=open_pos.entry_price,
                    exit_price=exit_px, lot=open_pos.lot,
                    profit_usd=p_usd, profit_pips=p_pips, exit_reason=exit_reason,
                ))
                equity += p_usd
                equity_curve.append(equity)
                last_trade_time = bar_time
                last_trade_dir = open_pos.direction
                open_pos = None

        # ── Skip entry checks if position open ───────────────────────────────
        if open_pos is not None:
            continue

        # ── Daily loss circuit-breaker ────────────────────────────────────────
        daily_loss_pct = ((daily_loss_start_equity - equity) / daily_loss_start_equity) * 100
        if daily_loss_pct >= config.max_daily_loss_pct:
            continue

        # ── Daily trade count cap ─────────────────────────────────────────────
        if daily_trades >= config.max_trades_per_day:
            continue

        # ── Hourly loss cap ───────────────────────────────────────────────────
        if config.max_loss_per_symbol_per_hour_pct > 0:
            cutoff = bar_time - timedelta(hours=1)
            recent_loss = sum(
                loss for t, loss in hourly_loss_tracker if t >= cutoff and loss < 0
            )
            hour_loss_pct = abs(recent_loss) / params.initial_equity * 100
            if hour_loss_pct >= config.max_loss_per_symbol_per_hour_pct:
                continue

        # ── Reverse cooldown ──────────────────────────────────────────────────
        if (
            config.reverse_cooldown_seconds > 0
            and last_trade_time is not None
            and last_trade_dir is not None
        ):
            elapsed = (bar_time - last_trade_time).total_seconds()
            if elapsed < config.reverse_cooldown_seconds:
                continue

        # ── Generate signal ───────────────────────────────────────────────────
        window = signal_bars.iloc[: i + 1]

        trend_window: Optional[pd.DataFrame] = None
        if trend_bars is not None:
            trend_window = slice_trend_at(trend_bars, bar["time"], min_bars=strategy_config.trend_ema + 4)

        signal = detect_signal_mtf(window, trend_window, strategy_config, config.symbol)

        if signal.type is SignalType.NONE:
            continue

        # ── Determine SL/TP ───────────────────────────────────────────────────
        entry_price = float(bar["close"])

        # Apply slippage
        if signal.type is SignalType.BUY:
            entry_price += params.slippage_pips * pip
        else:
            entry_price -= params.slippage_pips * pip

        if strategy_config.use_atr_sl_tp and signal.atr is not None:
            sl_pips = signal.atr / pip * strategy_config.atr_sl_multiplier
            tp_pips = signal.atr / pip * strategy_config.atr_tp_multiplier
        else:
            sl_pips = sl_pips_base
            tp_pips = tp_pips_base

        if signal.type is SignalType.BUY:
            sl_price = entry_price - sl_pips * pip
            tp_price = entry_price + tp_pips * pip
        else:
            sl_price = entry_price + sl_pips * pip
            tp_price = entry_price - tp_pips * pip

        # ── Lot size (reduce after consecutive losses) ────────────────────────
        effective_lot = lot
        if consecutive_losses >= config.max_consecutive_losses:
            effective_lot = round(lot * config.lot_reduction_factor, 2)
            effective_lot = max(effective_lot, 0.01)

        atr_at_entry = signal.atr

        open_pos = _OpenPosition(
            direction=signal.type, entry_price=entry_price,
            lot=effective_lot, sl=sl_price, tp=tp_price,
            entry_time=bar_time, initial_sl=sl_price, initial_tp=tp_price,
            atr_at_entry=atr_at_entry,
        )
        daily_trades += 1

    # ── Close any open position at end of data ────────────────────────────────
    if open_pos is not None and len(signal_bars) > 0:
        last_bar = signal_bars.iloc[-1]
        last_time = last_bar["time"].to_pydatetime() if hasattr(last_bar["time"], "to_pydatetime") else last_bar["time"]
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        exit_px = float(last_bar["close"])
        p_usd, p_pips = _profit_usd(open_pos.direction, open_pos.entry_price, exit_px, open_pos.lot, pip, pip_val)
        closed_trades.append(_ClosedTrade(
            entry_time=open_pos.entry_time, exit_time=last_time,
            direction=open_pos.direction, entry_price=open_pos.entry_price,
            exit_price=exit_px, lot=open_pos.lot,
            profit_usd=p_usd, profit_pips=p_pips, exit_reason="end_of_data",
        ))

    # ── Compute metrics ───────────────────────────────────────────────────────
    return _compute_metrics(closed_trades, equity_curve, sl_pips_base, params.initial_equity)


def _compute_metrics(
    trades: list[_ClosedTrade],
    equity_curve: list[float],
    sl_pips: float,
    initial_equity: float,
) -> PerformanceMetrics:
    if not trades:
        return PerformanceMetrics(
            trades=0, wins=0, losses=0, profit_factor=0.0, win_rate_pct=0.0,
            expectancy_pips=0.0, max_drawdown_pct=0.0, max_losing_streak=0,
            sharpe=0.0, sl_pips=sl_pips,
        )

    profits_usd = [t.profit_usd for t in trades]
    profits_pips = [t.profit_pips for t in trades]
    wins = sum(1 for p in profits_usd if p > 0)
    losses_count = sum(1 for p in profits_usd if p <= 0)
    gross_profit = sum(p for p in profits_usd if p > 0)
    gross_loss = abs(sum(p for p in profits_usd if p < 0))
    pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf")
    wr = round((wins / len(trades)) * 100, 2)
    exp_pips = round(sum(profits_pips) / len(profits_pips), 2)

    # Max drawdown as % of initial equity
    dd_usd = _max_drawdown(equity_curve)
    dd_pct = round((dd_usd / initial_equity) * 100, 2) if initial_equity > 0 else 0.0

    # Max consecutive losses
    streak = _max_losing_streak(profits_usd)

    # Sharpe — using per-trade returns
    if len(profits_usd) >= 2:
        mean_r = sum(profits_usd) / len(profits_usd)
        stdev_r = statistics.stdev(profits_usd)
        sharpe = round(mean_r / stdev_r, 2) if stdev_r > 0 else 0.0
    else:
        sharpe = 0.0

    return PerformanceMetrics(
        trades=len(trades),
        wins=wins,
        losses=losses_count,
        profit_factor=pf,
        win_rate_pct=wr,
        expectancy_pips=exp_pips,
        max_drawdown_pct=dd_pct,
        max_losing_streak=streak,
        sharpe=sharpe,
        sl_pips=sl_pips,
        source="backtest",
    )


def _max_losing_streak(profits: list[float]) -> int:
    max_streak = 0
    current = 0
    for p in profits:
        if p <= 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak
