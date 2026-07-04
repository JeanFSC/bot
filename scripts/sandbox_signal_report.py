from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"


def _fetch_rows(db_path: Path, table: str, limit: int = 20) -> list[dict]:
    if not db_path.exists():
        return []
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in con.execute(
            f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()]
    except sqlite3.Error:
        return []
    finally:
        con.close()


def _count(db_path: Path, table: str) -> int:
    if not db_path.exists():
        return 0
    con = sqlite3.connect(db_path)
    try:
        return int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except sqlite3.Error:
        return 0
    finally:
        con.close()


def _latest_created_at(db_path: Path, table: str) -> str | None:
    if not db_path.exists():
        return None
    con = sqlite3.connect(db_path)
    try:
        return con.execute(f"SELECT MAX(created_at) FROM {table}").fetchone()[0]
    except sqlite3.Error:
        return None
    finally:
        con.close()


def _recent_log_tail(log_path: Path, lines: int = 25) -> list[str]:
    if not log_path.exists():
        return []
    try:
        return log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    except OSError:
        return []


def render(payload: dict) -> str:
    lines = [
        "# Research Sandbox Signal Report",
        "",
        f"Generated: {payload['generated_at']}",
        f"Name: {payload['name']}",
        f"Database: {payload['database']}",
        f"Log: {payload['log']}",
        "",
        "## Counts",
        f"- Signals: {payload['counts']['signals']}",
        f"- Trade journal rows: {payload['counts']['trade_journal']}",
        f"- Order checks/sends: {payload['counts']['orders']}",
        f"- Latest signal: {payload['latest']['signals'] or 'none'}",
        f"- Latest journal: {payload['latest']['trade_journal'] or 'none'}",
        "",
        "## Latest Signals",
    ]
    if payload["signals"]:
        for row in payload["signals"]:
            lines.append(f"- {row.get('created_at')} {row.get('symbol')} {row.get('signal_type')} {row.get('reason')} price={row.get('price')}")
    else:
        lines.append("- None recorded yet.")

    lines += ["", "## Latest Trade Journal"]
    if payload["trade_journal"]:
        for row in payload["trade_journal"]:
            lines.append(
                f"- {row.get('created_at')} {row.get('symbol')} {row.get('signal_type')} "
                f"decision={row.get('decision')} reason={row.get('signal_reason')} exec={row.get('execution_status')}:{row.get('execution_reason')}"
            )
    else:
        lines.append("- None recorded yet.")

    lines += ["", "## Recent Log Tail"]
    if payload["log_tail"]:
        for line in payload["log_tail"]:
            lines.append(f"- {line[-220:]}")
    else:
        lines.append("- No log lines found.")

    lines += ["", "## Judge"]
    if payload["counts"]["signals"] == 0 and payload["counts"]["trade_journal"] == 0:
        lines.append("- WAITING: sandbox is running but no actionable signal/journal rows have been recorded yet.")
    elif payload["counts"]["orders"] > 0:
        lines.append("- REVIEW: dry-run created order-check/order rows; inspect them before any live promotion.")
    else:
        lines.append("- OBSERVE: telemetry exists; keep collecting until sample gate is met.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Report dry-run sandbox signal telemetry")
    parser.add_argument("--name", default="USDJPY London V2")
    parser.add_argument("--db", default="data/research_usdjpy_london_v2.sqlite")
    parser.add_argument("--log", default="logs/sandbox_usdjpy_london_v2.log")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    db_path = ROOT / args.db
    log_path = ROOT / args.log
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "name": args.name,
        "database": str(db_path),
        "log": str(log_path),
        "counts": {
            "signals": _count(db_path, "signals"),
            "trade_journal": _count(db_path, "trade_journal"),
            "orders": _count(db_path, "orders"),
        },
        "latest": {
            "signals": _latest_created_at(db_path, "signals"),
            "trade_journal": _latest_created_at(db_path, "trade_journal"),
        },
        "signals": _fetch_rows(db_path, "signals", 10),
        "trade_journal": _fetch_rows(db_path, "trade_journal", 10),
        "log_tail": _recent_log_tail(log_path),
    }
    text = render(payload)
    if args.write:
        REPORT_DIR.mkdir(exist_ok=True)
        (REPORT_DIR / "SANDBOX_SIGNAL_REPORT.md").write_text(text, encoding="utf-8")
        (REPORT_DIR / "sandbox_signal_report.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
