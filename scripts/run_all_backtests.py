#!/usr/bin/env python3
"""Run realistic backtests for all 12 bot configs and save results as JSON.

Usage (after running download_bars.py):

    python scripts/run_all_backtests.py --slippage 0.3 --json

Output: data/backtests/<SYMBOL>_<TIMEFRAME>.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

_CONFIGS = [
    ("config/pro.yaml",          "EURUSD", "M15", "H1"),
    ("config/pro_gbpusd.yaml",   "GBPUSD", "M15", "H1"),
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
    parser = argparse.ArgumentParser(description="Run all backtests")
    parser.add_argument("--bars-dir", default="data/bars")
    parser.add_argument("--out-dir", default="data/backtests")
    parser.add_argument("--slippage", type=float, default=0.3)
    parser.add_argument("--initial-equity", type=float, default=10_000.0)
    parser.add_argument("--lot", type=float, default=0.1)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    from mt5_bot.backtest_engine import run_realistic_backtest, BacktestParams
    from mt5_bot.bars_loader import load_bars_from_csv
    from mt5_bot.config import load_config
    from mt5_bot.performance import compute_score, suggestions

    bars_dir = Path(args.bars_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    params = BacktestParams(
        slippage_pips=args.slippage,
        initial_equity=args.initial_equity,
        lot_size=args.lot,
    )

    results = []
    for cfg_path, symbol, signal_tf, trend_tf in _CONFIGS:
        signal_csv = bars_dir / f"{symbol}_{signal_tf}.csv"
        trend_csv = bars_dir / f"{symbol}_{trend_tf}.csv"

        if not signal_csv.exists():
            print(f"SKIP {cfg_path}: {signal_csv} not found")
            continue

        print(f"Running {symbol} {signal_tf} ({cfg_path})...")
        try:
            config = load_config(cfg_path)
            signal_bars = load_bars_from_csv(signal_csv)
            trend_bars = load_bars_from_csv(trend_csv) if trend_csv.exists() else None
            metrics = run_realistic_backtest(signal_bars, config, trend_bars=trend_bars, params=params)
            score = compute_score(metrics)
            hints = suggestions(metrics)

            row = {
                "config": cfg_path,
                "symbol": symbol,
                "timeframe": signal_tf,
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
                f"  trades={metrics.trades} PF={metrics.profit_factor} "
                f"WR={metrics.win_rate_pct}% DD={metrics.max_drawdown_pct}% "
                f"SCORE={score}/10"
            )

        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)

    if args.as_json:
        print(json.dumps(results, indent=2))

    if results:
        avg = round(sum(r["score"] for r in results) / len(results), 2)
        print(f"\nPortfolio average score: {avg}/10 ({len(results)} bots)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
