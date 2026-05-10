#!/usr/bin/env python3
"""Download OHLCV bars from MetaTrader5 terminal and save as CSV.

Run this on your Windows machine where MetaTrader5 is installed:

    pip install MetaTrader5 pandas
    python scripts/download_bars.py --all --years 2 --include-trend

Output: data/bars/<SYMBOL>_<TIMEFRAME>.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


_CONFIGS = [
    ("EURUSD", "M15"), ("GBPUSD", "M15"), ("USDJPY", "M15"), ("GBPJPY", "M15"),
    ("AUDUSD", "M15"), ("NZDUSD", "M15"), ("USDCAD", "M15"), ("USDCHF", "M15"),
    ("XAUUSD", "M15"), ("XAUUSD", "M5"), ("XAGUSD", "M15"),
]
_TREND_TF = "H1"


def download_one(symbol: str, timeframe: str, years: int, out_dir: Path) -> Path:
    from mt5_bot.bars_loader import load_bars_from_mt5

    df = load_bars_from_mt5(symbol, timeframe, years=years)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{symbol}_{timeframe}.csv"
    df.to_csv(path, index=False)
    print(f"  Saved {len(df)} bars -> {path}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Download MT5 bars to CSV")
    parser.add_argument("--symbol", default=None, help="Single symbol (e.g. EURUSD)")
    parser.add_argument("--timeframe", default="M15", help="Timeframe (e.g. M15)")
    parser.add_argument("--all", action="store_true", dest="all_configs", help="Download all 12 bot pairs")
    parser.add_argument("--include-trend", action="store_true", help="Also download H1 trend bars")
    parser.add_argument("--years", type=int, default=2, help="Years of history to download")
    parser.add_argument("--out-dir", default="data/bars", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    pairs: list[tuple[str, str]] = []

    if args.all_configs:
        pairs = list(_CONFIGS)
        if args.include_trend:
            trend_symbols = {s for s, _ in _CONFIGS}
            for sym in trend_symbols:
                pairs.append((sym, _TREND_TF))
    elif args.symbol:
        pairs = [(args.symbol, args.timeframe)]
        if args.include_trend:
            pairs.append((args.symbol, _TREND_TF))
    else:
        parser.print_help()
        return 1

    # Deduplicate
    pairs = list(dict.fromkeys(pairs))

    print(f"Downloading {len(pairs)} bar series ({args.years}y) -> {out_dir}")
    for symbol, tf in pairs:
        print(f"  {symbol} {tf}...")
        try:
            download_one(symbol, tf, years=args.years, out_dir=out_dir)
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
