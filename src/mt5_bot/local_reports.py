from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


def collect_database_metrics(db_paths: Sequence[str | Path]) -> dict[str, Any]:
    totals = {"closed_trades": 0, "wins": 0, "losses": 0, "net_pnl": 0.0}
    symbols: dict[str, dict[str, Any]] = defaultdict(lambda: {"closed_trades": 0, "wins": 0, "losses": 0, "net_pnl": 0.0, "last_reason": None})
    postmortems: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()

    for raw_path in db_paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        try:
            if _table_exists(con, "deals"):
                for row in con.execute(
                    """
                    SELECT symbol, profit, commission, swap
                    FROM deals
                    WHERE entry = 1
                    """
                ).fetchall():
                    pnl = float(row["profit"] or 0.0) + float(row["commission"] or 0.0) + float(row["swap"] or 0.0)
                    if pnl == 0:
                        continue
                    symbol = row["symbol"] or "UNKNOWN"
                    totals["closed_trades"] += 1
                    totals["net_pnl"] += pnl
                    if pnl > 0:
                        totals["wins"] += 1
                        symbols[symbol]["wins"] += 1
                    else:
                        totals["losses"] += 1
                        symbols[symbol]["losses"] += 1
                    symbols[symbol]["closed_trades"] += 1
                    symbols[symbol]["net_pnl"] += pnl

            if _table_exists(con, "trade_journal"):
                for row in con.execute(
                    """
                    SELECT symbol, execution_reason
                    FROM trade_journal
                    ORDER BY created_at DESC
                    LIMIT 200
                    """
                ).fetchall():
                    symbol = row["symbol"] or "UNKNOWN"
                    reason = row["execution_reason"] or "unknown"
                    reason_counts[reason] += 1
                    if symbols[symbol]["last_reason"] is None:
                        symbols[symbol]["last_reason"] = reason

            if _table_exists(con, "trade_postmortems"):
                rows = con.execute(
                    """
                    SELECT created_at, symbol, pnl, severity, causes_json, actions_json, notes
                    FROM trade_postmortems
                    ORDER BY created_at DESC
                    LIMIT 20
                    """
                ).fetchall()
                for row in rows:
                    postmortems.append(
                        {
                            "created_at": row["created_at"],
                            "symbol": row["symbol"],
                            "pnl": float(row["pnl"]),
                            "severity": row["severity"],
                            "causes": json.loads(row["causes_json"]),
                            "actions": json.loads(row["actions_json"]),
                            "notes": row["notes"],
                        }
                    )
        finally:
            con.close()

    for payload in symbols.values():
        payload["net_pnl"] = round(float(payload["net_pnl"]), 2)
        trades = int(payload["closed_trades"])
        payload["win_rate_pct"] = round((payload["wins"] / trades) * 100, 2) if trades else None
    totals["net_pnl"] = round(float(totals["net_pnl"]), 2)
    totals["win_rate_pct"] = round((totals["wins"] / totals["closed_trades"]) * 100, 2) if totals["closed_trades"] else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "totals": totals,
        "symbols": dict(sorted(symbols.items())),
        "top_reasons": reason_counts.most_common(10),
        "postmortems": sorted(postmortems, key=lambda item: item["created_at"], reverse=True)[:20],
    }


def render_markdown_report(metrics: dict[str, Any], title: str = "MT5 Agent Local Report") -> str:
    totals = metrics["totals"]
    lines = [
        f"# {title}",
        "",
        f"Generated: `{metrics['generated_at']}`",
        "",
        "## Totals",
        "",
        f"- Closed trades: **{totals['closed_trades']}**",
        f"- Wins / Losses: **{totals['wins']} / {totals['losses']}**",
        f"- Win rate: **{totals['win_rate_pct'] if totals['win_rate_pct'] is not None else 'n/a'}%**",
        f"- Net P&L: **{totals['net_pnl']:.2f} USD**",
        "",
        "## Symbols",
        "",
        "| Symbol | Trades | W | L | Win rate | Net P&L | Last reason |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for symbol, row in metrics["symbols"].items():
        wr = "n/a" if row["win_rate_pct"] is None else f"{row['win_rate_pct']:.2f}%"
        lines.append(
            f"| {symbol} | {row['closed_trades']} | {row['wins']} | {row['losses']} | {wr} | {row['net_pnl']:.2f} | {row['last_reason'] or 'n/a'} |"
        )
    lines.extend(["", "## Top decision/block reasons", ""])
    if metrics["top_reasons"]:
        for reason, count in metrics["top_reasons"]:
            lines.append(f"- `{reason}`: {count}")
    else:
        lines.append("- n/a")

    lines.extend(["", "## Recent loss post-mortems", ""])
    if metrics["postmortems"]:
        for item in metrics["postmortems"][:10]:
            lines.extend(
                [
                    f"### {item['symbol']} {item['pnl']:.2f} USD ({item['severity']})",
                    f"- Causes: `{', '.join(item['causes'])}`",
                    f"- Corrective actions: `{', '.join(item['actions'])}`",
                    f"- Notes: {item['notes']}",
                    "",
                ]
            )
    else:
        lines.append("- No loss post-mortems yet.")
    return "\n".join(lines).rstrip() + "\n"


def write_local_report(db_paths: Sequence[str | Path], out_dir: str | Path, name: str = "local") -> dict[str, Path]:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    metrics = collect_database_metrics(db_paths)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output / f"{name}_{stamp}.json"
    markdown_path = output / f"{name}_{stamp}.md"
    latest_json = output / f"{name}_latest.json"
    latest_markdown = output / f"{name}_latest.md"
    json_text = json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True)
    md_text = render_markdown_report(metrics, title=f"MT5 Agent {name.title()} Report")
    for path, text in [(json_path, json_text), (latest_json, json_text), (markdown_path, md_text), (latest_markdown, md_text)]:
        path.write_text(text, encoding="utf-8")
    return {"json_path": json_path, "markdown_path": markdown_path, "latest_json_path": latest_json, "latest_markdown_path": latest_markdown}


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_local_reports")
    parser.add_argument("--out-dir", default="reports")
    parser.add_argument("--name", default="manual")
    parser.add_argument("db", nargs="+")
    args = parser.parse_args(argv)
    result = write_local_report(args.db, args.out_dir, args.name)
    print(f"LOCAL_REPORT markdown={result['markdown_path']} json={result['json_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
