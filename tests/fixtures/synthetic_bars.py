"""Synthetic OHLCV bar generators for testing."""
from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta


def _make_bar(time: datetime, open_: float, high: float, low: float, close: float) -> dict:
    return {"time": time, "open": open_, "high": high, "low": low, "close": close, "volume": 100.0}


def flat_bars(n: int = 200, price: float = 1.10000, spread: float = 0.0001) -> pd.DataFrame:
    """Flat market — no crossover signals should fire."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    for i in range(n):
        t = start + timedelta(minutes=15 * i)
        rows.append(_make_bar(t, price, price + spread, price - spread, price))
    return pd.DataFrame(rows)


def rally_bars(
    n: int = 300,
    start_price: float = 1.08000,
    pip: float = 0.0001,
    bar_size_pips: float = 5.0,
    flat_warmup: int = 40,
) -> pd.DataFrame:
    """Flat warmup then steady uptrend — crossover happens after min_bars.

    flat_warmup bars hold price flat so the EMA crossover fires after the
    backtest engine has enough warmup bars.
    """
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = start_price
    step = bar_size_pips * pip
    for i in range(flat_warmup):
        t = start + timedelta(minutes=15 * i)
        rows.append(_make_bar(t, price, price + pip, price - pip, price))
    for i in range(n):
        t = start + timedelta(minutes=15 * (flat_warmup + i))
        o = price
        c = price + step
        h = c + step * 0.5
        l = o - step * 0.2
        rows.append(_make_bar(t, o, h, l, c))
        price = c
    return pd.DataFrame(rows)


def drop_bars(
    n: int = 300,
    start_price: float = 1.12000,
    pip: float = 0.0001,
    bar_size_pips: float = 5.0,
    flat_warmup: int = 40,
) -> pd.DataFrame:
    """Flat warmup then steady downtrend — crossover happens after min_bars."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = start_price
    step = bar_size_pips * pip
    for i in range(flat_warmup):
        t = start + timedelta(minutes=15 * i)
        rows.append(_make_bar(t, price, price + pip, price - pip, price))
    for i in range(n):
        t = start + timedelta(minutes=15 * (flat_warmup + i))
        o = price
        c = price - step
        h = o + step * 0.2
        l = c - step * 0.5
        rows.append(_make_bar(t, o, h, l, c))
        price = c
    return pd.DataFrame(rows)


def alternating_crossover_bars(
    n_cycles: int = 10,
    pip: float = 0.0001,
    cycle_bars: int = 30,
) -> pd.DataFrame:
    """Alternating rally/drop cycles to generate multiple BUY/SELL signals."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    rows = []
    price = 1.10000
    step = 3.0 * pip
    i = 0
    for cycle in range(n_cycles):
        direction = 1 if cycle % 2 == 0 else -1
        for _ in range(cycle_bars):
            t = start + timedelta(minutes=15 * i)
            o = price
            c = price + direction * step
            h = max(o, c) + step * 0.3
            l = min(o, c) - step * 0.3
            rows.append(_make_bar(t, o, h, l, c))
            price = c
            i += 1
    return pd.DataFrame(rows)


def sl_hit_bars(
    entry_price: float = 1.10000,
    sl_pips: float = 20.0,
    pip: float = 0.0001,
    n_setup: int = 60,
) -> pd.DataFrame:
    """Bars that set up a BUY crossover then immediately drop to hit SL."""
    # First build a rally to get a BUY signal
    bars = rally_bars(n=n_setup, start_price=entry_price - sl_pips * pip * 3, pip=pip)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # Then add a sharp drop
    drop_start = bars["time"].iloc[-1] + timedelta(minutes=15)
    crash_low = entry_price - sl_pips * pip * 2
    extra = [
        _make_bar(drop_start, entry_price, entry_price + 0.0001, crash_low, crash_low + 0.0001),
    ]
    return pd.concat([bars, pd.DataFrame(extra)], ignore_index=True)


def tp_hit_bars(
    entry_price: float = 1.10000,
    tp_pips: float = 40.0,
    pip: float = 0.0001,
    n_setup: int = 60,
) -> pd.DataFrame:
    """Bars that set up a BUY crossover then surge to hit TP."""
    bars = rally_bars(n=n_setup, start_price=entry_price - tp_pips * pip * 3, pip=pip, bar_size_pips=3.0)
    surge_time = bars["time"].iloc[-1] + timedelta(minutes=15)
    surge_high = entry_price + tp_pips * pip * 2
    extra = [
        _make_bar(surge_time, entry_price, surge_high, entry_price - 0.0001, surge_high - 0.0001),
    ]
    return pd.concat([bars, pd.DataFrame(extra)], ignore_index=True)
