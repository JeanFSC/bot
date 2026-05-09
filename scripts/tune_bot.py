#!/usr/bin/env python3
"""Grid search tuning with in-sample / out-of-sample split.

Usage:
    python scripts/tune_bot.py \
        --config config/pro_gbpjpy.yaml \
        --bars data/bars/GBPJPY_M15.csv \
        --trend-bars data/bars/GBPJPY_H1.csv \
        --grid scripts/grids/gbpjpy.yaml \
        --train 2024-01-01..2024-09-30 \
        --test 2024-10-01..2024-12-31

Delta IS-OOS > 2 = likely overfit, discard.
"""
from __future__ import annotations

import argparse
import itertools
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _slice_bars(bars, start: datetime, end: datetime):
    mask = (bars["time"] >= start) & (bars["time"] <= end)
    return bars[mask].reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Grid search backtest tuner")
    parser.add_argument("--config", required=True)
    parser.add_argument("--bars", required=True)
    parser.add_argument("--trend-bars", default=None)
    parser.add_argument("--grid", required=True, help="YAML with parameter grid")
    parser.add_argument("--train", required=True, help="IS period: YYYY-MM-DD..YYYY-MM-DD")
    parser.add_argument("--test", required=True, help="OOS period: YYYY-MM-DD..YYYY-MM-DD")
    parser.add_argument("--slippage", type=float, default=0.3)
    parser.add_argument("--initial-equity", type=float, default=10_000.0)
    parser.add_argument("--lot", type=float, default=0.1)
    parser.add_argument("--top", type=int, default=10, help="Show top N combinations")
    parser.add_argument("--max-delta", type=float, default=2.0, help="Max IS-OOS delta before flagging overfit")
    args = parser.parse_args()

    import yaml
    from mt5_bot.backtest_engine import run_realistic_backtest, BacktestParams
    from mt5_bot.bars_loader import load_bars_from_csv
    from mt5_bot.config import load_config, StrategySettings
    from mt5_bot.performance import compute_score

    train_start, train_end = [_parse_date(d) for d in args.train.split("..")]
    test_start, test_end = [_parse_date(d) for d in args.test.split("..")]

    config = load_config(args.config)
    all_bars = load_bars_from_csv(args.bars)
    trend_all = load_bars_from_csv(args.trend_bars) if args.trend_bars else None

    train_bars = _slice_bars(all_bars, train_start, train_end)
    test_bars = _slice_bars(all_bars, test_start, test_end)
    trend_train = _slice_bars(trend_all, train_start, train_end) if trend_all is not None else None
    trend_test = _slice_bars(trend_all, test_start, test_end) if trend_all is not None else None

    grid_raw: dict[str, list[Any]] = yaml.safe_load(Path(args.grid).read_text())
    strategy_fields = set(StrategySettings.__dataclass_fields__)  # type: ignore[attr-defined]
    param_grid = {k: v for k, v in grid_raw.items() if k in strategy_fields}

    keys = list(param_grid.keys())
    combos = list(itertools.product(*[param_grid[k] for k in keys]))
    print(f"Grid: {len(combos)} combinations × 2 windows")

    params = BacktestParams(slippage_pips=args.slippage, initial_equity=args.initial_equity, lot_size=args.lot)
    results = []

    for combo in combos:
        overrides = dict(zip(keys, combo))
        new_strategy = replace(config.strategy, **overrides)
        cfg = replace(config, strategy=new_strategy)

        m_is = run_realistic_backtest(train_bars, cfg, trend_bars=trend_train, params=params)
        m_oos = run_realistic_backtest(test_bars, cfg, trend_bars=trend_test, params=params)
        is_score = compute_score(m_is)
        oos_score = compute_score(m_oos)
        delta = round(is_score - oos_score, 2)
        overfit = delta > args.max_delta

        results.append({
            "params": overrides,
            "is_score": is_score,
            "oos_score": oos_score,
            "delta": delta,
            "overfit": overfit,
            "is_trades": m_is.trades,
            "oos_trades": m_oos.trades,
            "is_pf": m_is.profit_factor,
            "oos_pf": m_oos.profit_factor,
        })

    results.sort(key=lambda r: r["oos_score"], reverse=True)

    print(f"\nTop {args.top} combinations (ranked by OOS score):\n")
    header = f"{'OOS':>6} {'IS':>6} {'Δ':>6} {'OVERFIT':>8}  params"
    print(header)
    print("-" * len(header))
    for r in results[: args.top]:
        flag = "⚠️ " if r["overfit"] else "ok"
        params_str = " ".join(f"{k}={v}" for k, v in r["params"].items())
        print(f"{r['oos_score']:>6.2f} {r['is_score']:>6.2f} {r['delta']:>6.2f} {flag:>8}  {params_str}")

    best = results[0]
    if not best["overfit"]:
        print(f"\nBest OOS: {best['oos_score']}/10 (delta={best['delta']})")
        print("Apply to YAML:")
        for k, v in best["params"].items():
            print(f"  {k}: {v}")
    else:
        print("\nAll top combinations show overfit (IS-OOS delta > max_delta). Try a coarser grid.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
