from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def generate_report(db_path: str | Path) -> dict[str, float | int | None]:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Database not found: {path}")

    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        total_signals = connection.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        total_checks = connection.execute("SELECT COUNT(*) FROM orders WHERE phase = 'check'").fetchone()[0]
        total_sends = connection.execute("SELECT COUNT(*) FROM orders WHERE phase = 'send'").fetchone()[0]
        avg_spread = connection.execute("SELECT AVG(spread_pips) FROM market_metrics").fetchone()[0]
        latest_equity = connection.execute("SELECT equity FROM account_snapshots ORDER BY id DESC LIMIT 1").fetchone()
        equity_rows = connection.execute("SELECT equity FROM account_snapshots WHERE equity IS NOT NULL ORDER BY id").fetchall()
        deal_rows = connection.execute("SELECT profit FROM deals WHERE profit IS NOT NULL").fetchall()
        send_rows = connection.execute("SELECT request_json, result_json FROM orders WHERE phase = 'send'").fetchall()
        rejection_rows = connection.execute(
            "SELECT retcode, comment, COUNT(*) AS count FROM orders WHERE phase = 'check' AND retcode NOT IN (0, 10008, 10009) GROUP BY retcode, comment"
        ).fetchall()

    profits = [float(row["profit"]) for row in deal_rows if float(row["profit"]) != 0.0]
    positive = sum(value for value in profits if value > 0)
    negative = abs(sum(value for value in profits if value < 0))
    trade_count = len(profits)
    wins = sum(1 for value in profits if value > 0)
    slippages = [_slippage_pips(row["request_json"], row["result_json"]) for row in send_rows]
    slippages = [value for value in slippages if value is not None]

    return {
        "total_signals": total_signals,
        "order_checks": total_checks,
        "orders_sent": total_sends,
        "avg_spread_pips": avg_spread,
        "latest_equity": latest_equity[0] if latest_equity else None,
        "profit_factor": round(positive / negative, 2) if negative > 0 else None,
        "win_rate_pct": round((wins / trade_count) * 100, 2) if trade_count else None,
        "expectancy": round(sum(profits) / trade_count, 2) if trade_count else None,
        "max_drawdown": round(_max_drawdown([float(row["equity"]) for row in equity_rows]), 2),
        "avg_slippage_pips": round(sum(slippages) / len(slippages), 2) if slippages else None,
        "rejection_reasons": len(rejection_rows),
    }


def format_report(metrics: dict[str, float | int | None]) -> str:
    return "\n".join(
        [
            "MT5 Bot Report",
            f"Signals: {metrics['total_signals']}",
            f"Order checks: {metrics['order_checks']}",
            f"Orders sent: {metrics['orders_sent']}",
            f"Average spread pips: {metrics['avg_spread_pips'] if metrics['avg_spread_pips'] is not None else 'n/a'}",
            f"Latest equity: {metrics['latest_equity'] if metrics['latest_equity'] is not None else 'n/a'}",
            f"Profit factor: {metrics['profit_factor'] if metrics['profit_factor'] is not None else 'n/a'}",
            f"Win rate: {metrics['win_rate_pct'] if metrics['win_rate_pct'] is not None else 'n/a'}%",
            f"Expectancy: {metrics['expectancy'] if metrics['expectancy'] is not None else 'n/a'}",
            f"Max drawdown: {metrics['max_drawdown']}",
            f"Average slippage pips: {metrics['avg_slippage_pips'] if metrics['avg_slippage_pips'] is not None else 'n/a'}",
            f"Rejected check groups: {metrics['rejection_reasons']}",
        ]
    )


def _max_drawdown(equity_values: list[float]) -> float:
    peak = None
    max_drawdown = 0.0
    for value in equity_values:
        peak = value if peak is None else max(peak, value)
        if peak:
            max_drawdown = max(max_drawdown, peak - value)
    return max_drawdown


def _slippage_pips(request_json: str, result_json: str) -> float | None:
    request = json.loads(request_json)
    result = json.loads(result_json)
    requested = request.get("price")
    executed = result.get("price")
    symbol = str(request.get("symbol", ""))
    # MT5 may return price=0 when the execution price is not yet available
    # (e.g. market orders on some demo servers). Skip those rows.
    if not requested or not executed:
        return None
    req_f = float(requested)
    exe_f = float(executed)
    if req_f == 0.0 or exe_f == 0.0:
        return None
    pip = 0.01 if symbol.endswith("JPY") else 0.0001
    return abs(exe_f - req_f) / pip
