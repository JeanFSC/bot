from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from mt5_bot.config import load_config
from mt5_bot.mt5_gateway import MT5Gateway
from mt5_bot.research_backtest import ResearchBacktestResult, run_research_backtest


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"

SESSION_WINDOWS = {
    "all": (None, None),
    "tokyo": (0, 6),
    "london": (7, 12),
    "ny": (13, 20),
    "overlap": (12, 16),
}


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _render(results: list[ResearchBacktestResult], since: str, until: str, session: str) -> str:
    lines = [
        "# Research Backtest - Fabio-Style Market Structure Proxies",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Window: {since} to {until}",
        f"Session: {session}",
        "",
        "Important: this is a research proxy. MT5 forex/CFD bars do not provide true footprint, CVD, or futures order-flow aggression.",
        "",
        "| Symbol | Trades | W | L | Net pips | Expectancy | PF | Avg win | Avg loss | Decision |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in sorted(results, key=lambda item: item.expectancy_pips, reverse=True):
        pf = "n/a" if row.profit_factor is None else f"{row.profit_factor:.2f}"
        decision = "candidate" if row.trades >= 10 and row.expectancy_pips > 0 and (row.profit_factor or 0) >= 1.25 else "reject_or_more_data"
        lines.append(
            f"| {row.symbol} | {row.trades} | {row.wins} | {row.losses} | {row.net_pips:.2f} | "
            f"{row.expectancy_pips:.2f} | {pf} | {row.avg_win:.2f} | {row.avg_loss:.2f} | {decision} |"
        )
    lines.extend(["", "## Breakdown By Setup / Session / Quality", ""])
    breakdown = _breakdown(results)
    if not breakdown:
        lines.append("- No trades.")
    else:
        lines.extend([
            "| Symbol | Session | Setup | Quality | Trades | W | L | Net pips | Expectancy | PF |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ])
        for item in breakdown:
            pf = "n/a" if item["profit_factor"] is None else f"{item['profit_factor']:.2f}"
            lines.append(
                f"| {item['symbol']} | {item['session']} | {item['setup']} | {item['quality']} | "
                f"{item['trades']} | {item['wins']} | {item['losses']} | {item['net_pips']:.2f} | "
                f"{item['expectancy_pips']:.2f} | {pf} |"
            )
    return "\n".join(lines) + "\n"


def _breakdown(results: list[ResearchBacktestResult]) -> list[dict[str, object]]:
    buckets: dict[tuple[str, str, str, str], list[float]] = {}
    for result in results:
        for trade in result.trades_detail:
            key = (trade.symbol, trade.session, trade.setup, trade.quality)
            buckets.setdefault(key, []).append(float(trade.pnl_pips))

    rows: list[dict[str, object]] = []
    for (symbol, session, setup, quality), values in buckets.items():
        wins = [v for v in values if v > 0]
        losses = [v for v in values if v <= 0]
        gross_win = sum(wins)
        gross_loss = abs(sum(losses))
        total = sum(values)
        rows.append({
            "symbol": symbol,
            "session": session,
            "setup": setup,
            "quality": quality,
            "trades": len(values),
            "wins": len(wins),
            "losses": len(losses),
            "net_pips": round(total, 2),
            "expectancy_pips": round(total / len(values), 2) if values else 0.0,
            "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else None,
        })
    return sorted(rows, key=lambda item: float(item["expectancy_pips"]), reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Research backtest for market-state/VWAP/profile setups")
    parser.add_argument("--configs", nargs="+", required=True)
    parser.add_argument("--from-date", default="2026-05-15")
    parser.add_argument("--to-date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--session", choices=sorted(SESSION_WINDOWS), default="all")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    gateway = MT5Gateway()
    gateway.initialize()
    results: list[ResearchBacktestResult] = []
    try:
        session_start, session_end = SESSION_WINDOWS[args.session]
        for config_path in args.configs:
            config = load_config(config_path)
            gateway.symbol_select(config.symbol)
            rates = gateway.copy_rates_range(
                config.symbol,
                config.timeframe,
                _parse_date(args.from_date),
                _parse_date(args.to_date),
            )
            if rates.empty:
                continue
            results.append(run_research_backtest(
                rates,
                config.symbol,
                session_name=args.session,
                session_start_hour=session_start,
                session_end_hour=session_end,
            ))
    finally:
        gateway.shutdown()

    text = _render(results, args.from_date, args.to_date, args.session)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "from_date": args.from_date,
        "to_date": args.to_date,
        "session": args.session,
        "breakdown": _breakdown(results),
        "results": [asdict(item) for item in results],
    }
    if args.write:
        REPORT_DIR.mkdir(exist_ok=True)
        (REPORT_DIR / "RESEARCH_BACKTEST.md").write_text(text, encoding="utf-8")
        (REPORT_DIR / "research_backtest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
