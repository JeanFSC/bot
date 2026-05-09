"""Tests for bars_loader.py."""
from __future__ import annotations

import io
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import pytest

from mt5_bot.bars_loader import load_bars_from_csv, align_mtf_bars, slice_trend_at


def _make_df(n: int, start: datetime, freq_minutes: int = 15) -> pd.DataFrame:
    times = [start + timedelta(minutes=freq_minutes * i) for i in range(n)]
    return pd.DataFrame({
        "time": times,
        "open": [1.1000 + i * 0.0001 for i in range(n)],
        "high": [1.1010 + i * 0.0001 for i in range(n)],
        "low":  [1.0990 + i * 0.0001 for i in range(n)],
        "close": [1.1005 + i * 0.0001 for i in range(n)],
        "volume": [100.0] * n,
    })


def test_load_bars_from_csv_roundtrip(tmp_path):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    df = _make_df(50, start)
    csv_path = tmp_path / "bars.csv"
    df.to_csv(csv_path, index=False)

    loaded = load_bars_from_csv(csv_path)
    assert len(loaded) == 50
    assert set(["time", "open", "high", "low", "close"]).issubset(loaded.columns)
    assert loaded["close"].dtype == float


def test_load_bars_from_csv_sorted(tmp_path):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    df = _make_df(10, start)
    # Shuffle rows
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    csv_path = tmp_path / "bars_shuffled.csv"
    df.to_csv(csv_path, index=False)

    loaded = load_bars_from_csv(csv_path)
    assert list(loaded["time"]) == sorted(loaded["time"])


def test_load_bars_missing_column(tmp_path):
    df = pd.DataFrame({"time": ["2024-01-01"], "open": [1.1], "high": [1.2], "close": [1.1]})
    csv_path = tmp_path / "bad.csv"
    df.to_csv(csv_path, index=False)
    with pytest.raises(ValueError, match="missing columns"):
        load_bars_from_csv(csv_path)


def test_load_bars_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_bars_from_csv("/nonexistent/path/bars.csv")


def test_align_mtf_bars_overlap():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    sig = _make_df(100, start, freq_minutes=15)
    # Trend bars start 10 hours later (so overlap begins at trend start)
    trend_start = start + timedelta(hours=10)
    trn = _make_df(50, trend_start, freq_minutes=60)

    sig_aligned, trn_aligned = align_mtf_bars(sig, trn)
    # Both aligned sets should start at the same lower bound
    assert sig_aligned["time"].min() >= trn_aligned["time"].min()
    # Signal bars within the overlap window should not exceed trend bars' range
    overlap_end = min(sig["time"].max(), trn["time"].max())
    assert sig_aligned["time"].max() <= overlap_end + timedelta(minutes=15)


def test_align_mtf_bars_no_overlap():
    start_a = datetime(2024, 1, 1, tzinfo=timezone.utc)
    start_b = datetime(2024, 6, 1, tzinfo=timezone.utc)
    sig = _make_df(10, start_a, freq_minutes=15)
    trn = _make_df(10, start_b, freq_minutes=60)
    with pytest.raises(ValueError, match="no overlapping"):
        align_mtf_bars(sig, trn)


def test_slice_trend_at_enough_bars():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    trn = _make_df(100, start, freq_minutes=60)
    at_time = pd.Timestamp(start + timedelta(hours=80))
    result = slice_trend_at(trn, at_time, min_bars=60)
    assert result is not None
    assert len(result) >= 60
    assert result["time"].max() <= at_time


def test_slice_trend_at_not_enough_bars():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    trn = _make_df(20, start, freq_minutes=60)
    at_time = pd.Timestamp(start + timedelta(hours=10))
    result = slice_trend_at(trn, at_time, min_bars=60)
    assert result is None
