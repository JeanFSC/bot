from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd


_REQUIRED_COLS = {"open", "high", "low", "close", "time"}


def _validate(df: pd.DataFrame, path: str) -> pd.DataFrame:
    missing = _REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"CSV {path} is missing columns: {missing}")
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["time"]):
        df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").reset_index(drop=True)
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    if "volume" not in df.columns:
        df["volume"] = 0.0
    return df


def load_bars_from_csv(path: str | Path) -> pd.DataFrame:
    """Load OHLCV bars from a CSV file.

    Expected columns: time, open, high, low, close[, volume].
    Returns a DataFrame sorted by time with UTC-aware datetime index column.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Bars CSV not found: {p}")
    df = pd.read_csv(p)
    return _validate(df, str(p))


def load_bars_from_mt5(
    symbol: str,
    timeframe_str: str,
    years: int = 2,
) -> pd.DataFrame:
    """Download OHLCV bars from a running MetaTrader5 terminal.

    Only works on the user's Windows machine with MetaTrader5 installed.
    Raises ImportError in environments without the MT5 library.
    """
    try:
        import MetaTrader5 as mt5  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "MetaTrader5 is not installed. Run this script on your Windows machine "
            "with: pip install MetaTrader5"
        ) from exc

    _TF_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    tf = _TF_MAP.get(timeframe_str.upper())
    if tf is None:
        raise ValueError(f"Unsupported timeframe: {timeframe_str}")

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

    from datetime import timezone, timedelta

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=years * 365)

    rates = mt5.copy_rates_range(symbol, tf, start, end)
    mt5.shutdown()

    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No data returned for {symbol} {timeframe_str}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.rename(columns={"tick_volume": "volume"})
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    return df[["time", "open", "high", "low", "close", "volume"]].reset_index(drop=True)


def align_mtf_bars(
    signal_bars: pd.DataFrame,
    trend_bars: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Align signal and trend DataFrames to overlapping time range.

    Returns (signal_bars_aligned, trend_bars_aligned) sorted by time,
    restricted to the intersection of their time ranges.
    """
    s_min = signal_bars["time"].min()
    s_max = signal_bars["time"].max()
    t_min = trend_bars["time"].min()
    t_max = trend_bars["time"].max()

    lo = max(s_min, t_min)
    hi = min(s_max, t_max)

    if lo > hi:
        raise ValueError(
            f"Signal bars [{s_min}, {s_max}] and trend bars [{t_min}, {t_max}] "
            "have no overlapping time range."
        )

    sig = signal_bars[(signal_bars["time"] >= lo) & (signal_bars["time"] <= hi)].reset_index(drop=True)
    trn = trend_bars[(trend_bars["time"] >= lo) & (trend_bars["time"] <= hi)].reset_index(drop=True)
    return sig, trn


def slice_trend_at(
    trend_bars: pd.DataFrame,
    at_time: "pd.Timestamp",
    min_bars: int = 60,
) -> Optional[pd.DataFrame]:
    """Return all trend bars with time <= at_time, or None if fewer than min_bars."""
    subset = trend_bars[trend_bars["time"] <= at_time]
    if len(subset) < min_bars:
        return None
    return subset.reset_index(drop=True)
