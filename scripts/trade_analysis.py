#!/usr/bin/env python3
"""Trade-level diagnostic report: where does the strategy bleed money?

Runs a single bot's backtest and groups closed trades by:
  - session (UTC hour bucket: Asia / London / LDN-NY overlap / NY / Quiet)
  - direction (BUY / SELL)
  - ADX bucket (<20, 20-30, 30-40, >40)
  - ATR bucket (low / mid / high - by quantile)
  - RSI bucket (<30, 30-50, 50-70, >70)
  - trend_bias (bullish / bearish / none)

For each bucket prints: trades, wins, PF, WR%, expectancy_pips, total_usd.
The goal is to identify pockets where the strategy actually has edge,
so we can keep those filters and disable the rest.

Usage:
    python scripts/trade_analysis.py \\
        --config config/pro.yaml \\
        --bars data/bars/EURUSD_M15.csv \\
        --trend-bars data/bars/EURUSD_H1.csv \\
        --max-bars 50000

Output:
    Console table per bucket dimension
    data/analysis/<symbol>_<timeframe>_trades.json (full trade dump)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _bucket_session(hour: int) -> str:
    if 0 <= hour < 7:    return "Asia (00-07)"
    if 7 <= hour < 12:   return "London (07-12)"
    if 12 <= hour < 17:  return "LDN+NY (12-17)"
    if 17 <= hour < 22:  return "NY (17-22)"
    return "Quiet (22-24)"


def _bucket_adx(adx: float | None) -> str:
    if adx is None:    return "n/a"
    if adx < 20:       return "<20 (range)"
    if adx < 30:       return "20-30"
    if adx < 40:       return "30-40"
    return ">=40 (strong)"


def _bucket_rsi(rsi: float | None) -> str:
    if rsi is None:    return "n/a"
    if rsi < 30:       return "<30 (oversold)"
    if rsi < 50:       return "30-50"
    if rsi < 70:       return "50-70"
    return ">=70 (overbought)"


def _bucket_atr(atr_pips: float | None, low_q: float, high_q: float) -> str:
    if atr_pips is None:           return "n/a"
    if atr_pips < low_q:           return f"low (<{low_q:.1f})"
    if atr_pips < high_q:          return f"mid ({low_q:.1f}-{high_q:.1f})"
    return f"high (>={high_q:.1f})"


def _stats(trades: list) -> dict:
    if not trades:
        return {"trades": 0, "wins": 0, "PF": 0.0, "WR%": 0.0, "exp_pips": 0.0, "total_usd": 0.0}
    profits_usd  = [t.profit_usd for t in trades]
    profits_pips = [t.profit_pips for t in trades]
    wins         = sum(1 for p in profits_usd if p > 0)
    gp           = sum(p for p in profits_usd if p > 0)
    gl           = abs(sum(p for p in profits_usd if p < 0))
    pf           = round(gp / gl, 2) if gl > 0 else float("inf")
    return {
        "trades": len(trades),
        "wins": wins,
        "PF": pf if pf != float("inf") else "inf",
        "WR%": round(wins / len(trades) * 100, 2),
        "exp_pips": round(sum(profits_pips) / len(profits_pips), 2),
        "total_usd": round(sum(profits_usd), 2),
    }


def _print_buckets(title: str, trades: list, key_fn, sort_by_key: bool = True) -> dict:
    print(f"\n=== {title} ===")
    buckets: dict[str, list] = defaultdict(list)
    for t in trades:
        buckets[key_fn(t)].append(t)

    keys = sorted(buckets.keys()) if sort_by_key else list(buckets.keys())
    rows = {}
    print(f"{'bucket':<22} {'trades':>7} {'wins':>5} {'PF':>6} {'WR%':>6} "
          f"{'exp_pips':>9} {'total_usd':>10}")
    print("-" * 72)
    for k in keys:
        s = _stats(buckets[k])
        rows[k] = s
        pf_str = f"{s['PF']}" if not isinstance(s["PF"], str) else s["PF"]
        print(f"{k:<22} {s['trades']:>7} {s['wins']:>5} {pf_str:>6} "
              f"{s['WR%']:>6} {s['exp_pips']:>9} {s['total_usd']:>10}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Trade-level bucketed analysis")
    parser.add_argument("--config", required=True)
    parser.add_argument("--bars", required=True)
    parser.add_argument("--trend-bars", default=None)
    parser.add_argument("--max-bars", type=int, default=None)
    parser.add_argument("--slippage", type=float, default=None)
    parser.add_argument("--broker-profile", default=None)
    parser.add_argument("--invert-signals", action="store_true")
    parser.add_argument("--initial-equity", type=float, default=10_000.0)
    parser.add_argument("--lot", type=float, default=0.1)
    parser.add_argument("--out-dir", default="data/analysis")
    args = parser.parse_args()

    from mt5_bot.backtest_engine import run_realistic_backtest, BacktestParams
    from mt5_bot.bars_loader import load_bars_from_csv
    from mt5_bot.broker_profile import BrokerProfile
    from mt5_bot.config import load_config
    from mt5_bot.performance import compute_score

    config = load_config(args.config)
    signal_bars = load_bars_from_csv(args.bars)
    trend_bars  = load_bars_from_csv(args.trend_bars) if args.trend_bars else None

    if args.max_bars and len(signal_bars) > args.max_bars:
        signal_bars = signal_bars.iloc[-args.max_bars:].reset_index(drop=True)
        if trend_bars is not None:
            min_time = signal_bars["time"].iloc[0]
            trend_bars = trend_bars[trend_bars["time"] >= min_time].reset_index(drop=True)

    # Broker profile
    if args.broker_profile == "":
        profile = BrokerProfile.empty()
    elif args.broker_profile is not None:
        profile = BrokerProfile.from_json(args.broker_profile)
    else:
        profile = BrokerProfile.auto_detect()

    if len(profile) > 0:
        print(f"[broker] Using {len(profile)} symbols from {profile.source}")
    if args.invert_signals:
        print("[DIAGNOSTIC] Signals INVERTED")

    params = BacktestParams(
        slippage_pips=args.slippage,
        initial_equity=args.initial_equity,
        lot_size=args.lot,
        broker_profile=profile,
        invert_signals=args.invert_signals,
    )

    trades: list = []
    metrics = run_realistic_backtest(
        signal_bars, config, trend_bars=trend_bars, params=params, out_trades=trades,
    )

    # -- Top-line -------------------------------------------------------------
    print(f"\n{'='*72}")
    print(f"{config.symbol} {config.timeframe}  |  {len(signal_bars):,} bars  |  "
          f"{len(trades)} trades")
    print(f"  PF={metrics.profit_factor}  WR={metrics.win_rate_pct}%  "
          f"exp={metrics.expectancy_pips} pips  "
          f"DD={metrics.max_drawdown_pct}%  "
          f"streak={metrics.max_losing_streak}  "
          f"score={compute_score(metrics)}/10")

    if not trades:
        print("\nNo trades - cannot bucket. Check filters/parameters.")
        return 1

    # -- Compute ATR quantiles for bucketing ----------------------------------
    atrs = sorted([t.signal_atr_pips for t in trades if t.signal_atr_pips is not None])
    if atrs:
        low_q  = atrs[len(atrs) // 3]
        high_q = atrs[2 * len(atrs) // 3]
    else:
        low_q = high_q = 0.0

    # -- Buckets --------------------------------------------------------------
    by_session   = _print_buckets("By session (UTC)",  trades, lambda t: _bucket_session(t.signal_hour))
    by_direction = _print_buckets("By direction",      trades, lambda t: t.direction.value)
    by_adx       = _print_buckets("By ADX",            trades, lambda t: _bucket_adx(t.signal_adx))
    by_atr       = _print_buckets("By ATR pips",       trades, lambda t: _bucket_atr(t.signal_atr_pips, low_q, high_q))
    by_rsi       = _print_buckets("By RSI",            trades, lambda t: _bucket_rsi(t.signal_rsi))
    by_trend     = _print_buckets("By H1 trend bias",  trades, lambda t: t.signal_trend_bias or "none")
    by_exit      = _print_buckets("By exit reason",    trades, lambda t: t.exit_reason)

    # -- Best/worst pockets ---------------------------------------------------
    print(f"\n=== Best/worst pockets (min 10 trades, finite PF) ===")
    pockets = []
    for label, rows in [("session", by_session), ("ADX", by_adx),
                        ("ATR", by_atr), ("RSI", by_rsi), ("trend", by_trend)]:
        for k, s in rows.items():
            if s["trades"] >= 10 and isinstance(s["PF"], (int, float)):
                pockets.append((s["PF"], label, k, s))
    pockets.sort(reverse=True)
    if not pockets:
        print("(not enough buckets with >=10 trades and finite PF to rank)")
    else:
        print("Top 5 PF (potential edge):")
        for pf, lbl, k, s in pockets[:5]:
            print(f"  {lbl:>8} = {k:<22} trades={s['trades']:>4} PF={pf:>5} WR={s['WR%']}%")
        print("Bottom 5 PF (potential filters to add):")
        for pf, lbl, k, s in reversed(pockets[-5:]):
            print(f"  {lbl:>8} = {k:<22} trades={s['trades']:>4} PF={pf:>5} WR={s['WR%']}%")

    # -- Save full trade dump -------------------------------------------------
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{config.symbol}_{config.timeframe}_trades.json"

    def _serialize(t):
        d = asdict(t)
        d["direction"] = t.direction.value
        d["entry_time"] = t.entry_time.isoformat() if hasattr(t.entry_time, "isoformat") else str(t.entry_time)
        d["exit_time"]  = t.exit_time.isoformat() if hasattr(t.exit_time, "isoformat") else str(t.exit_time)
        return d

    out_path.write_text(json.dumps({
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "bars_used": len(signal_bars),
        "trades_total": len(trades),
        "metrics": {
            "PF": metrics.profit_factor,
            "WR_pct": metrics.win_rate_pct,
            "exp_pips": metrics.expectancy_pips,
            "DD_pct": metrics.max_drawdown_pct,
            "streak": metrics.max_losing_streak,
            "sharpe": metrics.sharpe,
            "score": compute_score(metrics),
        },
        "buckets": {
            "session": by_session, "direction": by_direction,
            "adx": by_adx, "atr": by_atr, "rsi": by_rsi,
            "trend_bias": by_trend, "exit_reason": by_exit,
        },
        "trades": [_serialize(t) for t in trades],
    }, indent=2, default=str))
    print(f"\nSaved full trade dump: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
