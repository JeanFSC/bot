"""
strategy.py — Signal detection for MT5 Pro Bot
================================================
Multi-timeframe EMA crossover strategy with:
  • ADX trend-strength filter  — eliminates false signals in ranging markets
  • RSI momentum check         — RSI must be rising/falling in signal direction
  • H1 EMA(50) macro trend filter
  • RSI(14) overbought/oversold guard
  • ATR volatility gate
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import pandas as pd


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NONE = "NONE"


@dataclass(frozen=True)
class StrategyConfig:
    # ── Entry EMAs (on signal timeframe e.g. M15) ─────────────────────────────
    fast_ema: int = 9
    slow_ema: int = 21
    # ── Trend filter (higher timeframe, e.g. H1) ──────────────────────────────
    trend_ema: int = 50
    use_trend_filter: bool = False
    # ── RSI ───────────────────────────────────────────────────────────────────
    rsi_period: int = 14
    rsi_buy_max: float = 70
    rsi_sell_min: float = 30
    use_rsi_filter: bool = True
    # ── RSI momentum — RSI must be rising (BUY) or falling (SELL) ────────────
    use_rsi_momentum: bool = False
    # ── ATR volatility gate ───────────────────────────────────────────────────
    atr_period: int = 14
    min_atr_pips: float = 1.0
    use_atr_filter: bool = True
    # ── ATR-based dynamic SL / TP multipliers ─────────────────────────────────
    atr_sl_multiplier: float = 1.5
    atr_tp_multiplier: float = 3.0
    use_atr_sl_tp: bool = False
    # ── ADX trend-strength filter ──────────────────────────────────────────────
    adx_period: int = 14
    adx_min_value: float = 25.0
    use_adx_filter: bool = False
    # ── Session filter (UTC hours) ─────────────────────────────────────────────
    session_start_hour: int = 7
    session_end_hour: int = 20
    use_session_filter: bool = False
    # ── Second session window (e.g. Tokyo for USDJPY: 0-4 UTC) ───────────────
    session2_start_hour: int = 0
    session2_end_hour: int = 0      # 0 == disabled (start==end means disabled)
    use_session2: bool = False
    # ── Trailing stop ─────────────────────────────────────────────────────────
    use_trailing_stop: bool = False
    breakeven_atr_multiplier: float = 1.0
    trailing_atr_multiplier: float = 1.5
    # ── Retest filter timeout ─────────────────────────────────────────────────
    retest_timeout_bars: int = 0   # 0 = no timeout; N = expire pending retest after N bars


@dataclass(frozen=True)
class Signal:
    type: SignalType
    price: Optional[float]
    time: Optional[datetime]
    reason: str
    fast_ema: Optional[float]
    slow_ema: Optional[float]
    rsi: Optional[float]
    atr: Optional[float]
    atr_pips: Optional[float] = None
    trend_bias: Optional[str] = None
    adx: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# Indicator helpers
# ─────────────────────────────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def atr(rates: pd.DataFrame, period: int) -> pd.Series:
    high_low   = rates["high"] - rates["low"]
    high_close = (rates["high"] - rates["close"].shift()).abs()
    low_close  = (rates["low"]  - rates["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def adx(rates: pd.DataFrame, period: int) -> pd.Series:
    """Average Directional Index (Wilder). Values > 25 = trending market."""
    high = rates["high"]
    low  = rates["low"]
    prev_close = rates["close"].shift(1)

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)

    up   = high.diff()
    down = -low.diff()
    plus_dm  = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)

    alpha = 1.0 / period
    atr_w    = tr.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    plus_di  = 100 * plus_dm.ewm(alpha=alpha, min_periods=period, adjust=False).mean() / atr_w
    minus_di = 100 * minus_dm.ewm(alpha=alpha, min_periods=period, adjust=False).mean() / atr_w

    di_sum  = (plus_di + minus_di).replace(0, pd.NA)
    dx      = 100 * (plus_di - minus_di).abs() / di_sum
    return dx.ewm(alpha=alpha, min_periods=period * 2, adjust=False).mean()


# ─────────────────────────────────────────────────────────────────────────────
# Signal builders
# ─────────────────────────────────────────────────────────────────────────────

def _none(
    reason: str,
    fast_value: Optional[float] = None,
    slow_value: Optional[float] = None,
    rsi_value: Optional[float] = None,
    atr_value: Optional[float] = None,
    atr_pips_value: Optional[float] = None,
    trend_bias: Optional[str] = None,
    adx_value: Optional[float] = None,
) -> Signal:
    return Signal(
        SignalType.NONE, None, None, reason,
        fast_value, slow_value, rsi_value, atr_value,
        atr_pips_value, trend_bias, adx_value,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Core detection — single timeframe (backward compatible)
# ─────────────────────────────────────────────────────────────────────────────

def detect_signal(rates: pd.DataFrame, config: StrategyConfig) -> Signal:
    """Single-timeframe entry signal. Calls detect_signal_mtf without trend layer."""
    return detect_signal_mtf(rates, None, config)


def _pip_size_for_symbol(symbol: str) -> float:
    """Return the price movement represented by 1 pip for common MT5 symbols.

    Forex pairs are usually 0.0001, JPY pairs 0.01. Metals such as XAUUSD are
    commonly quoted with 0.01 as one pip/point on MT5. The previous forex-only
    fallback made Gold ATR ~100x too large, inflating dynamic SL/TP and trailing
    thresholds.
    """
    sym = symbol.upper().replace("/", "")
    if sym.startswith(("XAU", "XAG", "GOLD", "SILVER")):
        return 0.01
    if "JPY" in sym:
        return 0.01
    return 0.0001


# ─────────────────────────────────────────────────────────────────────────────
# Core detection — multi-timeframe (PRO)
# ─────────────────────────────────────────────────────────────────────────────

def detect_signal_mtf(
    signal_rates: pd.DataFrame,
    trend_rates: Optional[pd.DataFrame],
    config: StrategyConfig,
    symbol: str = "EURUSD",
) -> Signal:
    """Multi-timeframe signal detection.

    Filter pipeline (in order):
      1. Enough bars
      2. EMA crossover on last CLOSED bar ([-2])
      3. H1 trend alignment
      4. RSI overbought/oversold guard  (reason: rsi_buy_filter / rsi_sell_filter)
      5. RSI momentum                   (reason: rsi_momentum_not_rising/falling)
      6. ATR volatility gate
      7. ADX trend strength
    """
    pip = _pip_size_for_symbol(symbol)

    # ── Enough bars? — only count periods for enabled filters ────────────────
    needed = [config.slow_ema + 3]  # +3: need at least [-1], [-2], [-3]
    if config.use_rsi_filter or config.use_rsi_momentum:
        needed.append(config.rsi_period)
    if config.use_atr_filter or config.use_atr_sl_tp:
        needed.append(config.atr_period)
    if config.use_adx_filter:
        needed.append(config.adx_period * 2)
    min_bars = max(needed)
    if len(signal_rates) < min_bars:
        return _none("not_enough_bars")

    candles = signal_rates.copy()
    candles["fast_ema"] = ema(candles["close"], config.fast_ema)
    candles["slow_ema"] = ema(candles["close"], config.slow_ema)
    candles["rsi_val"]  = rsi(candles["close"], config.rsi_period)
    candles["atr_val"]  = atr(candles, config.atr_period)

    if config.use_adx_filter:
        candles["adx_val"] = adx(candles, config.adx_period)

    # Use the last CLOSED bar ([-2]); [-1] is the live unfinished bar
    previous = candles.iloc[-3]
    current  = candles.iloc[-2]

    fast_prev  = float(previous["fast_ema"])
    slow_prev  = float(previous["slow_ema"])
    fast_curr  = float(current["fast_ema"])
    slow_curr  = float(current["slow_ema"])
    rsi_curr   = None if pd.isna(current["rsi_val"]) else float(current["rsi_val"])
    rsi_prev   = None if pd.isna(previous["rsi_val"]) else float(previous["rsi_val"])
    atr_curr   = None if pd.isna(current["atr_val"]) else float(current["atr_val"])
    atr_pips_v = round(atr_curr / pip, 2) if atr_curr else None
    adx_curr: Optional[float] = None
    if config.use_adx_filter and "adx_val" in candles.columns:
        raw = current["adx_val"]
        adx_curr = None if pd.isna(raw) else float(raw)

    # ── Higher-timeframe trend filter ─────────────────────────────────────────
    trend_bias: Optional[str] = None
    if (
        config.use_trend_filter
        and trend_rates is not None
        and len(trend_rates) >= config.trend_ema + 4
    ):
        tc = trend_rates.copy()
        tc["trend_ema"] = ema(tc["close"], config.trend_ema)
        last_close_trend = float(tc["close"].iloc[-2])
        trend_ema_val    = float(tc["trend_ema"].iloc[-2])
        trend_bias = "bullish" if last_close_trend > trend_ema_val else "bearish"

    # ── EMA crossover (on last CLOSED bar) ────────────────────────────────────
    signal_type = SignalType.NONE
    reason = "no_closed_bar_crossover"

    if fast_prev <= slow_prev and fast_curr > slow_curr:
        signal_type = SignalType.BUY
        reason = "ema_cross_above"
    elif fast_prev >= slow_prev and fast_curr < slow_curr:
        signal_type = SignalType.SELL
        reason = "ema_cross_below"

    if signal_type is SignalType.NONE:
        return _none(reason, fast_curr, slow_curr, rsi_curr, atr_curr, atr_pips_v,
                     trend_bias, adx_curr)

    # ── Trend alignment ───────────────────────────────────────────────────────
    if config.use_trend_filter and trend_bias is not None:
        if signal_type is SignalType.BUY and trend_bias == "bearish":
            return _none("trend_filter_blocked_buy", fast_curr, slow_curr,
                         rsi_curr, atr_curr, atr_pips_v, trend_bias, adx_curr)
        if signal_type is SignalType.SELL and trend_bias == "bullish":
            return _none("trend_filter_blocked_sell", fast_curr, slow_curr,
                         rsi_curr, atr_curr, atr_pips_v, trend_bias, adx_curr)

    # ── RSI overbought/oversold guard ─────────────────────────────────────────
    if config.use_rsi_filter and rsi_curr is not None:
        if signal_type is SignalType.BUY and rsi_curr > config.rsi_buy_max:
            return _none("rsi_buy_filter", fast_curr, slow_curr, rsi_curr,
                         atr_curr, atr_pips_v, trend_bias, adx_curr)
        if signal_type is SignalType.SELL and rsi_curr < config.rsi_sell_min:
            return _none("rsi_sell_filter", fast_curr, slow_curr, rsi_curr,
                         atr_curr, atr_pips_v, trend_bias, adx_curr)

    # ── RSI momentum — RSI must move in signal direction ──────────────────────
    if config.use_rsi_momentum and rsi_curr is not None and rsi_prev is not None:
        if signal_type is SignalType.BUY and rsi_curr <= rsi_prev:
            return _none("rsi_momentum_not_rising", fast_curr, slow_curr,
                         rsi_curr, atr_curr, atr_pips_v, trend_bias, adx_curr)
        if signal_type is SignalType.SELL and rsi_curr >= rsi_prev:
            return _none("rsi_momentum_not_falling", fast_curr, slow_curr,
                         rsi_curr, atr_curr, atr_pips_v, trend_bias, adx_curr)

    # ── ATR volatility gate ───────────────────────────────────────────────────
    if config.use_atr_filter and atr_curr is not None:
        if atr_curr < config.min_atr_pips * pip:
            return _none("atr_too_low", fast_curr, slow_curr, rsi_curr,
                         atr_curr, atr_pips_v, trend_bias, adx_curr)

    # ── ADX trend-strength gate ───────────────────────────────────────────────
    if config.use_adx_filter:
        if adx_curr is None:
            return _none("adx_not_available", fast_curr, slow_curr, rsi_curr,
                         atr_curr, atr_pips_v, trend_bias, adx_curr)
        if adx_curr < config.adx_min_value:
            return _none(
                f"adx_weak_trend_{adx_curr:.1f}",
                fast_curr, slow_curr, rsi_curr, atr_curr, atr_pips_v,
                trend_bias, adx_curr,
            )

    # ── All filters passed — emit signal ──────────────────────────────────────
    try:
        bar_time = current["time"].to_pydatetime()
    except AttributeError:
        bar_time = current["time"]

    return Signal(
        type=signal_type,
        price=float(current["close"]),
        time=bar_time,
        reason=reason,
        fast_ema=fast_curr,
        slow_ema=slow_curr,
        rsi=rsi_curr,
        atr=atr_curr,
        atr_pips=atr_pips_v,
        trend_bias=trend_bias,
        adx=adx_curr,
    )
