#!/usr/bin/env python3
"""Run realistic backtests for all 12 bot configs and save results as JSON.

Usage (after running download_bars.py):

    python scripts/run_all_backtests.py --slippage 0.3 --json

Quick validation with the most recent N bars:

    python scripts/run_all_backtests.py --slippage 0.3 --max-bars 5000 --json

Output: data/backtests/<SYMBOL>_<TIMEFRAME>.json
Missing CSV files are skipped with a clear warning — the rest continue.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

_CONFIGS = [
    ("config/pro.yaml",          "EURUSD", "M15", "H1"),
    ("config/pro_gbp.yaml",      "GBPUSD", "M15", "H1"),
    ("config/pro_jpy.yaml",      "USDJPY", "M15", "H1"),
    ("config/pro_gbpjpy.yaml",   "GBPJPY", "M15", "H1"),
    ("config/pro_aud.yaml",      "AUDUSD", "M15", "H1"),
    ("config/pro_nzdusd.yaml",   "NZDUSD", "M15", "H1"),
    ("config/pro_usdcad.yaml",   "USDCAD", "M15", "H1"),
    ("config/pro_usdchf.yaml",   "USDCHF", "M15", "H1"),
    ("config/pro_gold.yaml",     "XAUUSD", "M15", "H1"),
    ("config/pro_gold_m5.yaml",  "XAUUSD", "M5",  "H1"),
    ("config/pro_silver.yaml",   "XAGUSD", "M15", "H1"),
    ("config/pro_jpy_asia.yaml", "USDJPY", "M15", "H1"),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run realistic backtests for all 12 bot configs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--bars-dir", default="data/bars")
    parser.add_argument("--out-dir", default="data/backtests")
    parser.add_argument("--slippage", type=float, default=0.3)
    parser.add_argument("--initial-equity", type=float, default=10_000.0)
    parser.add_argument("--lot", type=float, default=0.1)
    parser.add_argument(
        "--max-bars", type=int, default=None,
        help="Use only the last N bars per bot (e.g. 5000 for a quick run). "
             "Omit to use all available history.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="Print full results JSON to stdout at the end")
    args = parser.parse_args()

    from mt5_bot.backtest_engine import run_realistic_backtest, BacktestParams
    from mt5_bot.bars_loader import load_bars_from_csv
    from mt5_bot.config import load_config
    from mt5_bot.performance import compute_score, suggestions

    bars_dir = Path(args.bars_dir)
    out_dir  = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    params = BacktestParams(
        slippage_pips=args.slippage,
        initial_equity=args.initial_equity,
        lot_size=args.lot,
    )

    if args.max_bars:
        print(f"[quick mode] Using last {args.max_bars:,} bars per bot")

    results = []
    skipped = []
    errored = []
    total_start = time.perf_counter()

    for cfg_path, symbol, signal_tf, trend_tf in _CONFIGS:
        signal_csv = bars_dir / f"{symbol}_{signal_tf}.csv"
        trend_csv  = bars_dir / f"{symbol}_{trend_tf}.csv"

        if not signal_csv.exists():
            msg = f"SKIP [{symbol} {signal_tf}]: {signal_csv} not found - run download_bars.py first"
            print(f"WARN {msg}")
            skipped.append(f"{symbol} {signal_tf}")
            continue

        label = f"{symbol} {signal_tf}"
        print(f"Running {label} ({cfg_path})...", end="", flush=True)
        t0 = time.perf_counter()

        try:
            config      = load_config(cfg_path)
            signal_bars = load_bars_from_csv(signal_csv)
            trend_bars  = load_bars_from_csv(trend_csv) if trend_csv.exists() else None

            # Trim to last N bars if requested
            if args.max_bars and len(signal_bars) > args.max_bars:
                signal_bars = signal_bars.iloc[-args.max_bars:].reset_index(drop=True)
                if trend_bars is not None:
                    # Keep trend bars aligned to the same time range
                    min_time = signal_bars["time"].iloc[0]
                    trend_bars = trend_bars[trend_bars["time"] >= min_time].reset_index(drop=True)

            metrics = run_realistic_backtest(signal_bars, config, trend_bars=trend_bars, params=params)
            score   = compute_score(metrics)
            hints   = suggestions(metrics)
            elapsed = time.perf_counter() - t0

            row = {
                "config": cfg_path,
                "symbol": symbol,
                "timeframe": signal_tf,
                "bars_used": len(signal_bars),
                "trades": metrics.trades,
                "wins": metrics.wins,
                "losses": metrics.losses,
                "profit_factor": metrics.profit_factor,
                "win_rate_pct": metrics.win_rate_pct,
                "expectancy_pips": metrics.expectancy_pips,
                "max_drawdown_pct": metrics.max_drawdown_pct,
                "max_losing_streak": metrics.max_losing_streak,
                "sharpe": metrics.sharpe,
                "score": score,
                "suggestions": hints,
            }
            results.append(row)

            out_file = out_dir / f"{symbol}_{signal_tf}.json"
            out_file.write_text(json.dumps(row, indent=2))

            print(
                f" {elapsed:.1f}s | bars={len(signal_bars):,} trades={metrics.trades} "
                f"PF={metrics.profit_factor} WR={metrics.win_rate_pct}% "
                f"DD={metrics.max_drawdown_pct}% SCORE={score}/10"
            )

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            print(f" ERROR ({elapsed:.1f}s): {exc}", file=sys.stderr)
            errored.append(f"{symbol} {signal_tf}: {exc}")

    total_elapsed = time.perf_counter() - total_start

    if args.as_json:
        print(json.dumps(results, indent=2))

    print(f"\n{'-'*60}")
    if results:
        avg = round(sum(r["score"] for r in results) / len(results), 2)
        print(f"Portfolio average score: {avg}/10  ({len(results)} bots in {total_elapsed:.1f}s)")
    if skipped:
        print(f"Skipped ({len(skipped)}): {', '.join(skipped)}")
    if errored:
        print(f"Errors  ({len(errored)}):")
        for e in errored:
            print(f"  - {e}")
    if not results and not skipped:
        print("No bars data found. Run: python scripts/download_bars.py --all --years 2 --include-trend")

    return 0 if not errored else 1


if __name__ == "__main__":
    sys.exit(main())
