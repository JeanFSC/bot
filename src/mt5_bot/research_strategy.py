from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd

from mt5_bot.market_structure import anchored_vwap, classify_market_state, volume_profile
from mt5_bot.strategy import SignalType, atr, _pip_size_for_symbol


class ResearchSetup(str, Enum):
    TREND_CONTINUATION = "trend_continuation"
    VALUE_RECLAIM = "value_reclaim"


@dataclass(frozen=True)
class ResearchSignal:
    type: SignalType
    setup: Optional[ResearchSetup]
    quality: str
    reason: str
    entry: Optional[float]
    sl: Optional[float]
    tp: Optional[float]
    market_state: str
    vwap: Optional[float]
    poc: Optional[float]
    atr_value: Optional[float]


def _none(reason: str, market_state: str = "unknown") -> ResearchSignal:
    return ResearchSignal(
        type=SignalType.NONE,
        setup=None,
        quality="none",
        reason=reason,
        entry=None,
        sl=None,
        tp=None,
        market_state=market_state,
        vwap=None,
        poc=None,
        atr_value=None,
    )


def detect_research_signal(
    rates: pd.DataFrame,
    symbol: str,
    lookback: int = 48,
    atr_period: int = 14,
    sl_atr: float = 1.2,
    tp_atr: float = 2.4,
) -> ResearchSignal:
    """Detect a Fabio-inspired research signal from MT5 bar data.

    This is intentionally a research proxy, not true futures order flow. The
    original trader framework uses footprint/CVD/absorption. MT5 spot/CFD data
    usually lacks that, so this function uses deterministic substitutes:
    market state, VWAP location, volume-profile POC, candle reclaim/rejection,
    and ATR-defined invalidation.
    """
    min_bars = max(lookback + 5, atr_period * 2 + 5)
    if len(rates) < min_bars:
        return _none("not_enough_bars")

    market_state = classify_market_state(rates, symbol, lookback=lookback)
    if market_state == "unknown":
        return _none("market_state_unknown", market_state)

    closed = rates.iloc[:-1].copy()
    current = closed.iloc[-1]
    previous = closed.iloc[-2]
    profile_window = closed.iloc[-lookback:]
    vwap_series = anchored_vwap(profile_window)
    vwap = float(vwap_series.iloc[-1])
    profile = volume_profile(profile_window)
    poc = float(profile.poc)
    atr_series = atr(rates, atr_period)
    atr_value = float(atr_series.iloc[-2]) if not pd.isna(atr_series.iloc[-2]) else 0.0
    if atr_value <= 0:
        atr_value = _pip_size_for_symbol(symbol)

    close = float(current["close"])
    open_ = float(current["open"])
    high = float(current["high"])
    low = float(current["low"])
    prev_close = float(previous["close"])
    tol = 0.25 * atr_value

    bullish_reject = low <= vwap + tol and close > open_ and close >= vwap
    bearish_reject = high >= vwap - tol and close < open_ and close <= vwap
    above_value = close > vwap and close > poc
    below_value = close < vwap and close < poc

    if market_state == "imbalance_up" and bullish_reject and above_value:
        entry = close
        return ResearchSignal(
            type=SignalType.BUY,
            setup=ResearchSetup.TREND_CONTINUATION,
            quality="A" if prev_close > vwap else "B",
            reason="imbalance_up_vwap_pullback_reject",
            entry=entry,
            sl=entry - sl_atr * atr_value,
            tp=entry + tp_atr * atr_value,
            market_state=market_state,
            vwap=vwap,
            poc=poc,
            atr_value=atr_value,
        )

    if market_state == "imbalance_down" and bearish_reject and below_value:
        entry = close
        return ResearchSignal(
            type=SignalType.SELL,
            setup=ResearchSetup.TREND_CONTINUATION,
            quality="A" if prev_close < vwap else "B",
            reason="imbalance_down_vwap_pullback_reject",
            entry=entry,
            sl=entry + sl_atr * atr_value,
            tp=entry - tp_atr * atr_value,
            market_state=market_state,
            vwap=vwap,
            poc=poc,
            atr_value=atr_value,
        )

    prior_high = float(profile_window.iloc[:-1]["high"].max())
    prior_low = float(profile_window.iloc[:-1]["low"].min())
    failed_upside = prev_close > prior_high and close < prior_high and close < vwap
    failed_downside = prev_close < prior_low and close > prior_low and close > vwap

    if market_state == "balance" and failed_upside:
        entry = close
        target = min(poc, entry - tp_atr * atr_value)
        return ResearchSignal(
            type=SignalType.SELL,
            setup=ResearchSetup.VALUE_RECLAIM,
            quality="A" if close < poc else "B",
            reason="failed_upside_breakout_reclaim_value",
            entry=entry,
            sl=max(float(current["high"]), entry + sl_atr * atr_value),
            tp=target,
            market_state=market_state,
            vwap=vwap,
            poc=poc,
            atr_value=atr_value,
        )

    if market_state == "balance" and failed_downside:
        entry = close
        target = max(poc, entry + tp_atr * atr_value)
        return ResearchSignal(
            type=SignalType.BUY,
            setup=ResearchSetup.VALUE_RECLAIM,
            quality="A" if close > poc else "B",
            reason="failed_downside_breakout_reclaim_value",
            entry=entry,
            sl=min(float(current["low"]), entry - sl_atr * atr_value),
            tp=target,
            market_state=market_state,
            vwap=vwap,
            poc=poc,
            atr_value=atr_value,
        )

    return _none("no_research_setup", market_state)
