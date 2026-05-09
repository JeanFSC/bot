#!/usr/bin/env python3
"""Performance score dashboard — real metrics per bot.

Usage:
    # After running scripts/run_all_backtests.py:
    python qa_performance_score.py

    # Without any data (shows NO_DATA placeholders):
    python qa_performance_score.py --backtest-only

Live metrics are pulled from each bot's SQLite database (if it exists).
Backtest results are read from data/backtests/<SYMBOL>_<TIMEFRAME>.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

_BOTS = [
    {"name": "EURUSD M15",  "config": "config/pro.yaml",          "db": "data/pro.sqlite",          "magic": 260430, "bt_key": "EURUSD_M15"},
    {"name": "GBPUSD M15",  "config": "config/pro_gbpusd.yaml",   "db": "data/pro_gbpusd.sqlite",   "magic": 260431, "bt_key": "GBPUSD_M15"},
    {"name": "USDJPY M15",  "config": "config/pro_jpy.yaml",      "db": "data/pro_jpy.sqlite",      "magic": 260435, "bt_key": "USDJPY_M15"},
    {"name": "GBPJPY M15",  "config": "config/pro_gbpjpy.yaml",   "db": "data/pro_gbpjpy.sqlite",   "magic": 260432, "bt_key": "GBPJPY_M15"},
    {"name": "AUDUSD M15",  "config": "config/pro_aud.yaml",      "db": "data/pro_aud.sqlite",      "magic": 260436, "bt_key": "AUDUSD_M15"},
    {"name": "NZDUSD M15",  "config": "config/pro_nzdusd.yaml",   "db": "data/pro_nzdusd.sqlite",   "magic": 260437, "bt_key": "NZDUSD_M15"},
    {"name": "USDCAD M15",  "config": "config/pro_usdcad.yaml",   "db": "data/pro_usdcad.sqlite",   "magic": 260438, "bt_key": "USDCAD_M15"},
    {"name": "USDCHF M15",  "config": "config/pro_usdchf.yaml",   "db": "data/pro_usdchf.sqlite",   "magic": 260439, "bt_key": "USDCHF_M15"},
    {"name": "XAUUSD M15",  "config": "config/pro_gold.yaml",     "db": "data/pro_gold.sqlite",     "magic": 260433, "bt_key": "XAUUSD_M15"},
    {"name": "XAUUSD M5",   "config": "config/pro_gold_m5.yaml",  "db": "data/pro_gold_m5.sqlite",  "magic": 260434, "bt_key": "XAUUSD_M5"},
    {"name": "XAGUSD M15",  "config": "config/pro_silver.yaml",   "db": "data/pro_silver.sqlite",   "magic": 260440, "bt_key": "XAGUSD_M15"},
    {"name": "USDJPY Asia", "config": "config/pro_jpy_asia.yaml", "db": "data/pro_jpy_asia.sqlite", "magic": 260441, "bt_key": "USDJPY_M15"},
]

_BT_DIR = Path("data/backtests")
_NA = "N/A"


def _fmt(v, fmt=".2f") -> str:
    if v is None:
        return _NA
    try:
        return format(float(v), fmt)
    except (TypeError, ValueError):
        return _NA


def _load_backtest(bt_key: str) -> dict | None:
    p = _BT_DIR / f"{bt_key}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _load_live(db_path: str, magic: int) -> dict | None:
    from pathlib import Path as P
    p = P(db_path)
    if not p.exists():
        return None
    try:
        from mt5_bot.report import generate_report_per_magic
        return generate_report_per_magic(p, magic=magic)
    except Exception:
        return None


def _compute_live_score(live: dict) -> float | None:
    """Compute performance score from live report dict."""
    from mt5_bot.performance import PerformanceMetrics, compute_score
    tc = live.get("trade_count", 0) or 0
    if tc < 10:
        return None
    pf = live.get("profit_factor") or 0.0
    wr = live.get("win_rate_pct") or 0.0
    exp = live.get("expectancy") or 0.0  # live expectancy is in USD, convert to pips below
    dd = live.get("max_drawdown") or 0.0
    streak = live.get("max_losing_streak") or 0
    # Live expectancy is USD; approximate pips using a 10 USD/pip assumption
    exp_pips = exp / 10.0
    # DD is absolute USD; express as % of latest equity
    equity = live.get("latest_equity") or 10_000
    dd_pct = (dd / equity * 100) if equity > 0 else 0.0
    m = PerformanceMetrics(
        trades=tc, wins=live.get("wins", 0), losses=tc - live.get("wins", 0),
        profit_factor=pf, win_rate_pct=wr, expectancy_pips=exp_pips,
        max_drawdown_pct=dd_pct, max_losing_streak=streak, sharpe=0.0, sl_pips=20.0,
        source="live",
    )
    return compute_score(m)


def main() -> int:
    parser = argparse.ArgumentParser(description="Performance score dashboard")
    parser.add_argument("--backtest-only", action="store_true", help="Skip live DB lookup")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    from mt5_bot.performance import combine_scores, suggestions, PerformanceMetrics, compute_score

    rows = []
    for bot in _BOTS:
        bt = _load_backtest(bot["bt_key"])
        live = None if args.backtest_only else _load_live(bot["db"], bot["magic"])

        bt_pf  = _fmt(bt["profit_factor"] if bt else None)
        bt_wr  = _fmt(bt["win_rate_pct"] if bt else None)
        bt_dd  = _fmt(bt["max_drawdown_pct"] if bt else None)
        bt_score = bt["score"] if bt else None

        lv_pf  = _fmt(live["profit_factor"] if live else None)
        lv_wr  = _fmt(live["win_rate_pct"] if live else None)
        lv_score = _compute_live_score(live) if live else None

        if bt_score is not None and lv_score is not None:
            lv_trades = (live or {}).get("trade_count", 0) or 0
            # Approximate a metrics object for combine_scores
            bt_m = PerformanceMetrics(
                trades=bt.get("trades", 0), wins=bt.get("wins", 0), losses=bt.get("losses", 0),
                profit_factor=bt.get("profit_factor") or 0.0,
                win_rate_pct=bt.get("win_rate_pct") or 0.0,
                expectancy_pips=bt.get("expectancy_pips") or 0.0,
                max_drawdown_pct=bt.get("max_drawdown_pct") or 0.0,
                max_losing_streak=bt.get("max_losing_streak") or 0,
                sharpe=bt.get("sharpe") or 0.0, sl_pips=20.0,
            )
            lv_m = PerformanceMetrics(
                trades=lv_trades, wins=0, losses=0,
                profit_factor=float(live.get("profit_factor") or 0),
                win_rate_pct=float(live.get("win_rate_pct") or 0),
                expectancy_pips=float(live.get("expectancy") or 0) / 10.0,
                max_drawdown_pct=float(live.get("max_drawdown") or 0) / float(live.get("latest_equity") or 10000) * 100,
                max_losing_streak=int(live.get("max_losing_streak") or 0),
                sharpe=0.0, sl_pips=20.0, source="live",
            )
            final_score = combine_scores(bt_m, lv_m)
        elif bt_score is not None:
            final_score = bt_score
        else:
            final_score = None

        hints: list[str] = []
        if bt:
            bt_m2 = PerformanceMetrics(
                trades=bt.get("trades", 0), wins=bt.get("wins", 0), losses=bt.get("losses", 0),
                profit_factor=bt.get("profit_factor") or 0.0,
                win_rate_pct=bt.get("win_rate_pct") or 0.0,
                expectancy_pips=bt.get("expectancy_pips") or 0.0,
                max_drawdown_pct=bt.get("max_drawdown_pct") or 0.0,
                max_losing_streak=bt.get("max_losing_streak") or 0,
                sharpe=bt.get("sharpe") or 0.0, sl_pips=20.0,
            )
            hints = suggestions(bt_m2)

        rows.append({
            "bot": bot["name"],
            "live_pf": lv_pf, "bt_pf": bt_pf,
            "live_wr": lv_wr, "bt_wr": bt_wr,
            "bt_dd": bt_dd,
            "score": _fmt(final_score) if final_score is not None else _NA,
            "hints": hints,
        })

    if args.as_json:
        print(json.dumps(rows, indent=2))
        return 0

    # ── Table ────────────────────────────────────────────────────────────────
    w = {"bot": 14, "live_pf": 8, "bt_pf": 8, "live_wr": 8, "bt_wr": 8, "bt_dd": 6, "score": 7}
    header = (
        f"{'BOT':<{w['bot']}} {'LV_PF':>{w['live_pf']}} {'BT_PF':>{w['bt_pf']}} "
        f"{'LV_WR%':>{w['live_wr']}} {'BT_WR%':>{w['bt_wr']}} {'DD%':>{w['bt_dd']}} "
        f"{'SCORE':>{w['score']}} {'NEEDS'}"
    )
    sep = "-" * len(header)
    print("\n" + sep)
    print(header)
    print(sep)

    scores = []
    for r in rows:
        needs = " | ".join(r["hints"]) if r["hints"] else "ok"
        print(
            f"{r['bot']:<{w['bot']}} {r['live_pf']:>{w['live_pf']}} {r['bt_pf']:>{w['bt_pf']}} "
            f"{r['live_wr']:>{w['live_wr']}} {r['bt_wr']:>{w['bt_wr']}} {r['bt_dd']:>{w['bt_dd']}} "
            f"{r['score']:>{w['score']}} {needs}"
        )
        try:
            scores.append(float(r["score"]))
        except (ValueError, TypeError):
            pass

    print(sep)
    if scores:
        avg = round(sum(scores) / len(scores), 2)
        print(f"\nPortfolio average score: {avg}/10  ({len(scores)}/{len(rows)} bots with data)\n")
    else:
        print("\nNo backtest data found. Run scripts/run_all_backtests.py first.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
