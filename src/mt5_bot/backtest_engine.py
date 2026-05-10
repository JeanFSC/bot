"""
backtest_engine.py — Realistic bar-by-bar backtest simulator.

Features replicated from the live executor:
  • SL / TP resolved intra-bar (conservative: SL wins ties)
  • ATR-based dynamic SL/TP when use_atr_sl_tp=True
  • Multi-timeframe trend filter (H1 EMA, mirrors detect_signal_mtf pipeline)
  • Session filter
  • Slippage (fixed pips deducted from entry)
  • Partial close (partial_close_ratio of position closed at first TP touch)
  • Trailing stop (after breakeven_atr_multiplier×ATR favourable move)
  • Reverse cooldown between opposite-direction trades
  • Max consecutive losses guard (lot_reduction_factor applied but trade allowed)
  • Max daily loss circuit-breaker (no new trades after hit)
  • Hourly cap (max_loss_per_symbol_per_hour_pct)

Performance: all indicators are pre-computed once (O(n)) and stored as numpy
arrays. The main loop does only O(1) array reads per bar, making the total
complexity O(n log n) — fast enough for 2 years of M15 bars in < 5s.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from mt5_bot.broker_profile import BrokerProfile
from mt5_bot.config import BotConfig
from mt5_bot.performance import PerformanceMetrics
from mt5_bot.report import _max_drawdown
from mt5_bot.strategy import (
    SignalType,
    StrategyConfig,
    _pip_size_for_symbol,
    ema,
    rsi,
    atr as atr_fn,
    adx as adx_fn,
)


# ── Pip-value table (USD per lot per pip) ───────────────────────────────────
# Computed as: tick_value * (pip_size / tick_size).
# For standard retail brokers (IC Markets / OANDA / Pepperstone class):
#   FX major:   100,000 base × 0.0001 pip × $1/tick = $10/pip
#   USDJPY:     100,000 × 0.01 / quote ≈ $9.1/pip (varies with USD/JPY rate)
#   XAUUSD:     100 oz × $0.01/pip = $1/pip       ← was 10.0 (10× bug)
#   XAGUSD:     5,000 oz × $0.01/pip = $50/pip
# Verify per-broker with scripts/diag_symbol_specs.py — ±5% tolerance expected.
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
    "XAUUSD": 1.0,
    "XAGUSD": 50.0,
}


# ── Per-symbol slippage defaults (pips) ──────────────────────────────────────
# Used when BacktestParams.slippage_pips is None. Reflects typical retail
# broker spreads applied to entry. Verify with scripts/diag_symbol_specs.py.
_DEFAULT_SLIPPAGE_PIPS: dict[str, float] = {
    "EURUSD": 1.0,
    "GBPUSD": 1.2,
    "AUDUSD": 1.0,
    "NZDUSD": 1.5,
    "USDCAD": 1.5,
    "USDCHF": 1.8,
    "USDJPY": 1.0,
    "GBPJPY": 2.0,
    "EURJPY": 1.5,
    "XAUUSD": 30.0,
    "XAGUSD": 5.0,
}


def _slippage_for_symbol(symbol: str, override: Optional[float]) -> float:
    if override is not None:
        return override
    return _DEFAULT_SLIPPAGE_PIPS.get(symbol.upper(), 1.0)


def _resolve_pip_value(symbol: str, profile: Optional[BrokerProfile]) -> float:
    """Broker profile wins; falls back to hardcoded _PIP_VALUE_PER_LOT."""
    fallback = _pip_value(symbol)
    if profile is not None:
        return profile.pip_value(symbol, fallback)
    return fallback


def _resolve_slippage(
    symbol: str,
    override: Optional[float],
    profile: Optional[BrokerProfile],
) -> float:
    """Override > broker profile > hardcoded per-symbol default."""
    if override is not None:
        return override
    fallback = _DEFAULT_SLIPPAGE_PIPS.get(symbol.upper(), 1.0)
    if profile is not None:
        return profile.slippage(symbol, fallback)
    return fallback


def _pip_value(symbol: str) -> float:
    sym = symbol.upper().replace("/", "")
    return _PIP_VALUE_PER_LOT.get(sym, 10.0)


@dataclass
class BacktestParams:
    slippage_pips: Optional[float] = None       # None -> per-symbol or broker profile
    initial_equity: float = 10_000.0
    lot_size: float = 0.1
    broker_profile: Optional[BrokerProfile] = None
    invert_signals: bool = False                # diagnostic: BUY <-> SELL


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


# ── Pre-computation helpers ──────────────────────────────────────────────────

def _precompute_signal_indicators(df: pd.DataFrame, sc: StrategyConfig) -> dict[str, np.ndarray]:
    """Compute all indicator series on the full bar DataFrame once.

    Returns a dict of numpy arrays indexed by bar position.
    """
    out: dict[str, np.ndarray] = {}
    out["fast_ema"] = ema(df["close"], sc.fast_ema).values
    out["slow_ema"] = ema(df["close"], sc.slow_ema).values
    out["rsi"]      = rsi(df["close"], sc.rsi_period).values
    out["atr"]      = atr_fn(df, sc.atr_period).values
    if sc.use_adx_filter:
        out["adx"] = adx_fn(df, sc.adx_period).values
    if sc.use_volatility_regime:
        out["atr50"] = pd.Series(out["atr"]).rolling(50, min_periods=1).mean().values
    return out


def _precompute_trend(trend_bars: pd.DataFrame, sc: StrategyConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pre-compute trend EMA and return (times, closes, emas) as numpy arrays."""
    tdf = trend_bars.copy()
    tdf["trend_ema_"] = ema(tdf["close"], sc.trend_ema)
    return tdf["time"].values, tdf["close"].values, tdf["trend_ema_"].values


def _to_datetime(ts) -> datetime:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        dt = pd.Timestamp(ts).to_pydatetime()
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.utcnow().replace(tzinfo=timezone.utc)


# ── Inlined signal check (mirrors detect_signal_mtf filter pipeline) ─────────

def _check_signal(
    i: int,
    ind: dict[str, np.ndarray],
    bar_time: datetime,
    sc: StrategyConfig,
    pip: float,
    trend_data: Optional[tuple[np.ndarray, np.ndarray, np.ndarray]],
    bar_time_raw,  # numpy datetime64 for searchsorted
) -> SignalType:
    """Return BUY, SELL or NONE. Mirrors the detect_signal_mtf filter pipeline.

    Uses pre-computed numpy arrays; O(1) per call (O(log m) for trend lookup).
    signal bar = i-1 (last closed), reference bar = i-2 (previous closed).
    """
    # Need at least 3 bars behind us
    if i < 3:
        return SignalType.NONE

    fast_curr = ind["fast_ema"][i - 1]
    slow_curr = ind["slow_ema"][i - 1]
    fast_prev = ind["fast_ema"][i - 2]
    slow_prev = ind["slow_ema"][i - 2]

    if np.isnan(fast_curr) or np.isnan(slow_curr) or np.isnan(fast_prev) or np.isnan(slow_prev):
        return SignalType.NONE

    # ── Volatility regime filter ──────────────────────────────────────────────
    if sc.use_volatility_regime and "atr50" in ind:
        atr_curr = ind["atr"][i - 1]
        atr50    = ind["atr50"][i - 1]
        if not np.isnan(atr_curr) and not np.isnan(atr50) and atr50 > 0:
            if atr_curr > atr50 * 2.5:
                return SignalType.NONE

    # ── EMA crossover (last closed bar) ──────────────────────────────────────
    if fast_prev <= slow_prev and fast_curr > slow_curr:
        signal_type = SignalType.BUY
    elif fast_prev >= slow_prev and fast_curr < slow_curr:
        signal_type = SignalType.SELL
    else:
        return SignalType.NONE

    # ── H1 trend filter ───────────────────────────────────────────────────────
    if sc.use_trend_filter and trend_data is not None:
        trend_times, trend_closes, trend_emas = trend_data
        # Find last trend bar at or before bar_time; use the one before it (closed)
        j = int(np.searchsorted(trend_times, bar_time_raw, side="right")) - 1
        if j >= 1 and j < len(trend_closes):
            trend_bias = "bullish" if trend_closes[j - 1] > trend_emas[j - 1] else "bearish"
            if signal_type is SignalType.BUY and trend_bias == "bearish":
                return SignalType.NONE
            if signal_type is SignalType.SELL and trend_bias == "bullish":
                return SignalType.NONE

    # ── RSI guard ─────────────────────────────────────────────────────────────
    if sc.use_rsi_filter:
        rsi_curr = ind["rsi"][i - 1]
        if not np.isnan(rsi_curr):
            if signal_type is SignalType.BUY and rsi_curr > sc.rsi_buy_max:
                return SignalType.NONE
            if signal_type is SignalType.SELL and rsi_curr < sc.rsi_sell_min:
                return SignalType.NONE

    # ── RSI momentum ──────────────────────────────────────────────────────────
    if sc.use_rsi_momentum:
        rsi_curr = ind["rsi"][i - 1]
        rsi_prev = ind["rsi"][i - 2]
        if not np.isnan(rsi_curr) and not np.isnan(rsi_prev):
            if signal_type is SignalType.BUY and rsi_curr <= rsi_prev:
                return SignalType.NONE
            if signal_type is SignalType.SELL and rsi_curr >= rsi_prev:
                return SignalType.NONE

    # ── ATR volatility gate ───────────────────────────────────────────────────
    if sc.use_atr_filter:
        atr_curr = ind["atr"][i - 1]
        if not np.isnan(atr_curr) and atr_curr < sc.min_atr_pips * pip:
            return SignalType.NONE

    # ── ADX gate ─────────────────────────────────────────────────────────────
    if sc.use_adx_filter and "adx" in ind:
        adx_curr = ind["adx"][i - 1]
        if np.isnan(adx_curr) or adx_curr < sc.adx_min_value:
            return SignalType.NONE

    # ── Session filter ────────────────────────────────────────────────────────
    if sc.use_session_filter:
        h = bar_time.hour
        in_s1 = sc.session_start_hour <= h < sc.session_end_hour
        in_s2 = (
            sc.use_session2
            and sc.session2_start_hour != sc.session2_end_hour
            and sc.session2_start_hour <= h < sc.session2_end_hour
        )
        if not in_s1 and not in_s2:
            return SignalType.NONE

    return signal_type


# ── Position management helpers ──────────────────────────────────────────────

def _resolve_sl_tp_intrabar(pos: _OpenPosition, bar_high: float, bar_low: float) -> Optional[str]:
    """Conservative: SL wins if both SL and TP hit in the same bar."""
    if pos.direction is SignalType.BUY:
        if bar_low <= pos.sl:
            return "sl"
        if bar_high >= pos.tp:
            return "tp"
    else:
        if bar_high >= pos.sl:
            return "sl"
        if bar_low <= pos.tp:
            return "tp"
    return None


def _trailing_update(
    pos: _OpenPosition,
    bar_close: float,
    bar_low: float,
    bar_high: float,
    sc: StrategyConfig,
    atr_val: Optional[float],
) -> _OpenPosition:
    if not sc.use_trailing_stop or atr_val is None or np.isnan(atr_val):
        return pos

    breakeven_dist = sc.breakeven_atr_multiplier * atr_val
    trailing_dist  = sc.trailing_atr_multiplier * atr_val

    if pos.direction is SignalType.BUY:
        move = bar_close - pos.entry_price
        if not pos.trailing_active and move >= breakeven_dist:
            pos = _replace_pos(pos, trailing_active=True, trailing_sl=pos.entry_price)
        if pos.trailing_active:
            new_sl = bar_close - trailing_dist
            current_sl = pos.trailing_sl if pos.trailing_sl is not None else pos.sl
            if new_sl > current_sl:
                pos = _replace_pos(pos, trailing_sl=new_sl, sl=new_sl)
    else:
        move = pos.entry_price - bar_close
        if not pos.trailing_active and move >= breakeven_dist:
            pos = _replace_pos(pos, trailing_active=True, trailing_sl=pos.entry_price)
        if pos.trailing_active:
            new_sl = bar_close + trailing_dist
            current_sl = pos.trailing_sl if pos.trailing_sl is not None else pos.sl
            if new_sl < current_sl:
                pos = _replace_pos(pos, trailing_sl=new_sl, sl=new_sl)
    return pos


def _replace_pos(pos: _OpenPosition, **kwargs) -> _OpenPosition:
    for k, v in kwargs.items():
        object.__setattr__(pos, k, v)
    return pos


def _profit_usd(
    direction: SignalType, entry: float, exit_price: float,
    lot: float, pip: float, pip_val: float,
) -> tuple[float, float]:
    if direction is SignalType.BUY:
        pips = (exit_price - entry) / pip
    else:
        pips = (entry - exit_price) / pip
    return round(pips * lot * pip_val, 2), round(pips, 2)


# ── Main backtest function ────────────────────────────────────────────────────

def run_realistic_backtest(
    signal_bars: pd.DataFrame,
    config: BotConfig,
    trend_bars: Optional[pd.DataFrame] = None,
    params: Optional[BacktestParams] = None,
) -> PerformanceMetrics:
    """Run a bar-by-bar backtest and return PerformanceMetrics.

    signal_bars and trend_bars must have columns: time, open, high, low, close.
    time must be UTC-aware datetime (or UTC naive — will be treated as UTC).

    All indicators are pre-computed once (O(n)), making the loop O(n log n).
    """
    if params is None:
        params = BacktestParams()

    sc = StrategyConfig(**{
        f: getattr(config.strategy, f)
        for f in StrategyConfig.__dataclass_fields__  # type: ignore[attr-defined]
    })

    pip     = _pip_size_for_symbol(config.symbol)
    pip_val = _resolve_pip_value(config.symbol, params.broker_profile)
    slippage_pips = _resolve_slippage(config.symbol, params.slippage_pips, params.broker_profile)
    sl_pips_base = config.risk.sl_pips
    tp_pips_base = config.risk.tp_pips
    lot = params.lot_size

    # ── Pre-compute indicators (one pass, O(n)) ───────────────────────────────
    df = signal_bars.reset_index(drop=True)
    ind = _precompute_signal_indicators(df, sc)

    # Raw numpy arrays for price data — O(1) indexing in loop
    close_arr = df["close"].values.astype(float)
    high_arr  = df["high"].values.astype(float)
    low_arr   = df["low"].values.astype(float)
    time_arr  = df["time"].values  # numpy datetime64 for searchsorted

    # Pre-convert times to Python datetime for cooldown/hourly arithmetic
    bar_datetimes: list[datetime] = [_to_datetime(t) for t in time_arr]

    # ── Pre-compute trend EMA (one pass, O(m)) ────────────────────────────────
    trend_data: Optional[tuple[np.ndarray, np.ndarray, np.ndarray]] = None
    if trend_bars is not None and sc.use_trend_filter:
        trend_data = _precompute_trend(trend_bars, sc)

    # ── Warmup: enough bars for the slowest indicator ─────────────────────────
    needed = [sc.slow_ema + 3]
    if sc.use_rsi_filter or sc.use_rsi_momentum:
        needed.append(sc.rsi_period)
    if sc.use_atr_filter or sc.use_atr_sl_tp or sc.use_trailing_stop:
        needed.append(sc.atr_period)
    if sc.use_adx_filter:
        needed.append(sc.adx_period * 2)
    if sc.use_volatility_regime:
        needed.append(50 + sc.atr_period)
    min_bars = max(needed) + 1  # +1 so i-1 and i-2 are both past warmup

    closed_trades: list[_ClosedTrade] = []
    equity = params.initial_equity
    equity_curve: list[float] = [equity]
    open_pos: Optional[_OpenPosition] = None

    last_trade_time: Optional[datetime] = None
    last_trade_dir: Optional[SignalType] = None
    consecutive_losses: int = 0
    daily_loss_start_equity: float = equity
    current_trade_date = None
    daily_trades: int = 0
    hourly_loss_tracker: list[tuple[datetime, float]] = []

    for i in range(min_bars, len(df)):
        bar_time  = bar_datetimes[i]
        bar_close = close_arr[i]
        bar_high  = high_arr[i]
        bar_low   = low_arr[i]
        atr_i     = ind["atr"][i]
        atr_val   = None if np.isnan(atr_i) else float(atr_i)

        # ── Daily reset ──────────────────────────────────────────────────────
        trade_date = bar_time.date()
        if current_trade_date != trade_date:
            current_trade_date = trade_date
            daily_loss_start_equity = equity
            daily_trades = 0

        # ── Manage open position ─────────────────────────────────────────────
        if open_pos is not None:
            open_pos = _trailing_update(open_pos, bar_close, bar_low, bar_high, sc, atr_val)
            exit_reason = _resolve_sl_tp_intrabar(open_pos, bar_high, bar_low)

            if exit_reason == "tp":
                exit_px = open_pos.tp
                if config.use_partial_close and not open_pos.partial_closed:
                    partial_lot = max(round(open_pos.lot * config.partial_close_ratio, 2), 0.01)
                    p_usd, p_pips = _profit_usd(open_pos.direction, open_pos.entry_price, exit_px, partial_lot, pip, pip_val)
                    closed_trades.append(_ClosedTrade(
                        entry_time=open_pos.entry_time, exit_time=bar_time,
                        direction=open_pos.direction, entry_price=open_pos.entry_price,
                        exit_price=exit_px, lot=partial_lot,
                        profit_usd=p_usd, profit_pips=p_pips, exit_reason="partial_tp",
                    ))
                    equity += p_usd
                    remaining_lot = max(round(open_pos.lot - partial_lot, 2), 0.01)
                    open_pos = _OpenPosition(
                        direction=open_pos.direction, entry_price=open_pos.entry_price,
                        lot=remaining_lot,
                        sl=open_pos.entry_price,
                        tp=open_pos.tp + (open_pos.tp - open_pos.entry_price),
                        entry_time=open_pos.entry_time, initial_sl=open_pos.initial_sl,
                        initial_tp=open_pos.initial_tp, atr_at_entry=open_pos.atr_at_entry,
                        partial_closed=True, trailing_active=open_pos.trailing_active,
                        trailing_sl=open_pos.trailing_sl,
                    )
                    equity_curve.append(equity)
                    continue
                p_usd, p_pips = _profit_usd(open_pos.direction, open_pos.entry_price, exit_px, open_pos.lot, pip, pip_val)
                consecutive_losses = 0

            elif exit_reason == "sl":
                exit_px = open_pos.sl
                p_usd, p_pips = _profit_usd(open_pos.direction, open_pos.entry_price, exit_px, open_pos.lot, pip, pip_val)
                consecutive_losses += 1
                hourly_loss_tracker.append((bar_time, p_usd))

            elif open_pos.trailing_active and open_pos.trailing_sl is not None:
                ts_hit = (
                    (open_pos.direction is SignalType.BUY  and bar_low  <= open_pos.trailing_sl)
                    or (open_pos.direction is SignalType.SELL and bar_high >= open_pos.trailing_sl)
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
                        profit_usd=p_usd, profit_pips=p_pips, exit_reason="trailing",
                    ))
                    equity += p_usd
                    equity_curve.append(equity)
                    last_trade_time = bar_time
                    last_trade_dir  = open_pos.direction
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
                last_trade_dir  = open_pos.direction
                open_pos = None

        if open_pos is not None:
            continue

        # ── Daily loss circuit-breaker ────────────────────────────────────────
        if daily_loss_start_equity > 0:
            daily_loss_pct = (daily_loss_start_equity - equity) / daily_loss_start_equity * 100
            if daily_loss_pct >= config.max_daily_loss_pct:
                continue

        if daily_trades >= config.max_trades_per_day:
            continue

        # ── Hourly loss cap ───────────────────────────────────────────────────
        if config.max_loss_per_symbol_per_hour_pct > 0:
            cutoff = bar_time - timedelta(hours=1)
            recent_loss = sum(loss for t, loss in hourly_loss_tracker if t >= cutoff and loss < 0)
            if abs(recent_loss) / params.initial_equity * 100 >= config.max_loss_per_symbol_per_hour_pct:
                continue

        # ── Reverse cooldown ──────────────────────────────────────────────────
        if config.reverse_cooldown_seconds > 0 and last_trade_time is not None:
            if (bar_time - last_trade_time).total_seconds() < config.reverse_cooldown_seconds:
                continue

        # ── Signal check (O(1) + O(log m) trend lookup) ──────────────────────
        signal_type = _check_signal(i, ind, bar_time, sc, pip, trend_data, time_arr[i])

        if signal_type is SignalType.NONE:
            continue

        # Diagnostic: flip signal direction (used to test "anti-edge" hypothesis)
        if params.invert_signals:
            signal_type = SignalType.SELL if signal_type is SignalType.BUY else SignalType.BUY

        # ── Entry price ───────────────────────────────────────────────────────
        entry_price = bar_close
        if signal_type is SignalType.BUY:
            entry_price += slippage_pips * pip
        else:
            entry_price -= slippage_pips * pip

        # ── SL / TP ───────────────────────────────────────────────────────────
        if sc.use_atr_sl_tp and atr_val is not None:
            sl_pips = atr_val / pip * sc.atr_sl_multiplier
            tp_pips = atr_val / pip * sc.atr_tp_multiplier
        else:
            sl_pips = sl_pips_base
            tp_pips = tp_pips_base

        if signal_type is SignalType.BUY:
            sl_price = entry_price - sl_pips * pip
            tp_price = entry_price + tp_pips * pip
        else:
            sl_price = entry_price + sl_pips * pip
            tp_price = entry_price - tp_pips * pip

        # ── Lot reduction after streak ────────────────────────────────────────
        effective_lot = lot
        if consecutive_losses >= config.max_consecutive_losses:
            effective_lot = max(round(lot * config.lot_reduction_factor, 2), 0.01)

        open_pos = _OpenPosition(
            direction=signal_type, entry_price=entry_price,
            lot=effective_lot, sl=sl_price, tp=tp_price,
            entry_time=bar_time, initial_sl=sl_price, initial_tp=tp_price,
            atr_at_entry=atr_val,
        )
        daily_trades += 1

    # ── Close any open position at end of data ────────────────────────────────
    if open_pos is not None and len(df) > 0:
        last_time  = bar_datetimes[-1]
        exit_px    = close_arr[-1]
        p_usd, p_pips = _profit_usd(open_pos.direction, open_pos.entry_price, exit_px, open_pos.lot, pip, pip_val)
        closed_trades.append(_ClosedTrade(
            entry_time=open_pos.entry_time, exit_time=last_time,
            direction=open_pos.direction, entry_price=open_pos.entry_price,
            exit_price=exit_px, lot=open_pos.lot,
            profit_usd=p_usd, profit_pips=p_pips, exit_reason="end_of_data",
        ))

    return _compute_metrics(closed_trades, equity_curve, sl_pips_base, params.initial_equity)


# ── Metrics computation ───────────────────────────────────────────────────────

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

    profits_usd  = [t.profit_usd for t in trades]
    profits_pips = [t.profit_pips for t in trades]
    wins         = sum(1 for p in profits_usd if p > 0)
    losses_count = sum(1 for p in profits_usd if p <= 0)
    gross_profit = sum(p for p in profits_usd if p > 0)
    gross_loss   = abs(sum(p for p in profits_usd if p < 0))

    pf      = round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf")
    wr      = round(wins / len(trades) * 100, 2)
    exp_pips = round(sum(profits_pips) / len(profits_pips), 2)

    dd_usd = _max_drawdown(equity_curve)
    dd_pct = round(dd_usd / initial_equity * 100, 2) if initial_equity > 0 else 0.0

    streak = _max_losing_streak(profits_usd)

    if len(profits_usd) >= 2:
        mean_r  = sum(profits_usd) / len(profits_usd)
        stdev_r = statistics.stdev(profits_usd)
        sharpe  = round(mean_r / stdev_r, 2) if stdev_r > 0 else 0.0
    else:
        sharpe = 0.0

    return PerformanceMetrics(
        trades=len(trades), wins=wins, losses=losses_count,
        profit_factor=pf, win_rate_pct=wr, expectancy_pips=exp_pips,
        max_drawdown_pct=dd_pct, max_losing_streak=streak,
        sharpe=sharpe, sl_pips=sl_pips, source="backtest",
    )


def _max_losing_streak(profits: list[float]) -> int:
    max_streak = current = 0
    for p in profits:
        if p <= 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak
