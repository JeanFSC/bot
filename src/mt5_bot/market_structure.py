from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from mt5_bot.strategy import atr, _pip_size_for_symbol


MarketState = Literal["balance", "imbalance_up", "imbalance_down", "unknown"]


@dataclass(frozen=True)
class VolumeProfile:
    poc: float
    hvn: list[float]
    lvn: list[float]


def _price_series(rates: pd.DataFrame) -> pd.Series:
    return (rates["high"].astype(float) + rates["low"].astype(float) + rates["close"].astype(float)) / 3.0


def _volume_series(rates: pd.DataFrame) -> pd.Series:
    if "real_volume" in rates.columns and rates["real_volume"].astype(float).sum() > 0:
        return rates["real_volume"].astype(float)
    if "tick_volume" in rates.columns:
        return rates["tick_volume"].astype(float)
    return pd.Series([1.0] * len(rates), index=rates.index)


def anchored_vwap(rates: pd.DataFrame, anchor_index: int = 0) -> pd.Series:
    """Return VWAP from anchor_index onward using typical price and available volume."""
    if rates.empty:
        return pd.Series(dtype=float)
    sliced = rates.iloc[max(anchor_index, 0):].copy()
    price = _price_series(sliced)
    volume = _volume_series(sliced).replace(0, 1.0)
    return (price * volume).cumsum() / volume.cumsum()


def volume_profile(rates: pd.DataFrame, bins: int = 24) -> VolumeProfile:
    """Approximate volume profile from OHLCV bars.

    MT5 forex data normally lacks true footprint/order-flow prints. This is an
    approximation from tick volume, useful for research/backtests but not a
    substitute for futures depth/footprint data.
    """
    if rates.empty:
        raise ValueError("rates must not be empty")
    if bins < 4:
        raise ValueError("bins must be >= 4")

    price = _price_series(rates)
    volume = _volume_series(rates)
    bucket = pd.cut(price, bins=bins)
    grouped = volume.groupby(bucket, observed=False).sum()
    centers = [float(interval.mid) for interval in grouped.index]
    values = grouped.to_list()
    ranked = sorted(zip(centers, values), key=lambda item: item[1], reverse=True)
    poc = ranked[0][0]
    hvn = [x[0] for x in ranked[: max(1, bins // 6)]]
    lvn = [x[0] for x in sorted(zip(centers, values), key=lambda item: item[1])[: max(1, bins // 6)]]
    return VolumeProfile(poc=poc, hvn=hvn, lvn=lvn)


def classify_market_state(
    rates: pd.DataFrame,
    symbol: str,
    lookback: int = 48,
    balance_atr_multiple: float = 3.0,
    breakout_atr_multiple: float = 0.6,
) -> MarketState:
    """Classify recent bars into a simple balance/imbalance regime.

    This converts the Fabio-style idea of auction state into a deterministic
    proxy that can be tested on MT5 bar data: tight range around value is
    balance; a close outside the prior range with ATR-sized displacement is
    imbalance.
    """
    if len(rates) < max(lookback + 2, 20):
        return "unknown"

    pip = _pip_size_for_symbol(symbol)
    window = rates.iloc[-lookback - 1:-1]
    current = rates.iloc[-2]
    prior = rates.iloc[-lookback - 2:-2]
    atr_series = atr(rates, 14)
    atr_value = float(atr_series.iloc[-2]) if not pd.isna(atr_series.iloc[-2]) else 0.0
    if atr_value <= 0:
        atr_value = pip

    range_size = float(window["high"].max() - window["low"].min())
    if range_size <= balance_atr_multiple * atr_value:
        return "balance"

    prior_high = float(prior["high"].max())
    prior_low = float(prior["low"].min())
    close = float(current["close"])
    previous_close = float(rates.iloc[-3]["close"])
    displacement = abs(close - previous_close)

    if close > prior_high and displacement >= breakout_atr_multiple * atr_value:
        return "imbalance_up"
    if close < prior_low and displacement >= breakout_atr_multiple * atr_value:
        return "imbalance_down"
    return "unknown"
