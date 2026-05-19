from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"

MAGIC_LABELS = {
    260433: "EURUSD",
    260434: "GBPUSD",
    260435: "USDJPY",
    260436: "XAUUSD",
    260437: "AUDUSD",
    260440: "XAUUSD_M5",
    260441: "USDCAD",
    260442: "NZDUSD",
    260443: "GBPJPY",
    260444: "XAGUSD",
    260445: "USDJPY_ASIA",
    260446: "USDCHF",
}

SUCCESS_RETCODES = {"10009", "10008"}
CRITICAL_PATTERNS = (
    "Traceback",
    "NameError",
    "RuntimeError",
    "CRITICAL",
    "IPC send failed",
    "Unhandled exception",
    "Bot crasheo",
)


def run_ps(script: str) -> str:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def suite_processes() -> list[dict[str, Any]]:
    script = r"""
$items = Get-CimInstance Win32_Process | Where-Object {
  ($_.Name -match 'python|pythonw|cmd|wscript|cscript') -and
  ($_.CommandLine -match 'mt5_bot trade|WATCHDOG_SAFE_24H|_restart_|_run_all_pro_autorestart|START_REDUCED_FORWARD_TEST')
} | Select-Object ProcessId,Name,CommandLine
$items | ConvertTo-Json -Compress
"""
    raw = run_ps(script)
    if not raw:
        return []
    data = json.loads(raw)
    return [data] if isinstance(data, dict) else list(data)


def mt5_snapshot(since: datetime) -> dict[str, Any]:
    try:
        import MetaTrader5 as mt5
    except Exception as exc:
        return {"available": False, "error": f"MetaTrader5 import failed: {exc}"}

    if not mt5.initialize():
        return {"available": False, "error": f"mt5.initialize failed: {mt5.last_error()}"}

    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        positions = mt5.positions_get() or []
        deals = mt5.history_deals_get(since, datetime.now(timezone.utc) + timedelta(hours=6)) or []
        by_magic: dict[int, dict[str, Any]] = defaultdict(lambda: {
            "label": "",
            "closed": 0,
            "wins": 0,
            "losses": 0,
            "pnl": 0.0,
            "gross_win": 0.0,
            "gross_loss": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "expectancy": 0.0,
        })
        for deal in deals:
            magic = int(getattr(deal, "magic", 0) or 0)
            if magic not in MAGIC_LABELS:
                continue
            profit = float(getattr(deal, "profit", 0.0) or 0.0)
            if profit == 0.0:
                continue
            row = by_magic[magic]
            row["label"] = MAGIC_LABELS[magic]
            row["closed"] += 1
            row["pnl"] += profit
            if profit > 0:
                row["wins"] += 1
                row["gross_win"] += profit
            else:
                row["losses"] += 1
                row["gross_loss"] += profit

        for row in by_magic.values():
            wins = int(row["wins"])
            losses = int(row["losses"])
            closed = int(row["closed"])
            row["avg_win"] = (float(row["gross_win"]) / wins) if wins else 0.0
            row["avg_loss"] = (float(row["gross_loss"]) / losses) if losses else 0.0
            row["expectancy"] = (float(row["pnl"]) / closed) if closed else 0.0

        return {
            "available": True,
            "account": account._asdict() if account else None,
            "terminal": terminal._asdict() if terminal else None,
            "positions": [p._asdict() for p in positions],
            "by_magic": dict(by_magic),
        }
    finally:
        mt5.shutdown()


def recent_log_findings(minutes: int) -> list[dict[str, str]]:
    cutoff = datetime.now().timestamp() - minutes * 60
    findings: list[dict[str, str]] = []
    for path in sorted((ROOT / "logs").glob("*.log")):
        try:
            if path.stat().st_mtime < cutoff:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]
        except Exception:
            continue
        for line in lines:
            if any(pattern in line for pattern in CRITICAL_PATTERNS):
                # retcode_10009 is success; do not classify it as an error.
                if any(f"retcode_{code}" in line for code in SUCCESS_RETCODES):
                    continue
                findings.append({"file": path.name, "line": line[-260:]})
                break
    return findings


def db_freshness() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for db in sorted((ROOT / "data").glob("pro*.sqlite")):
        item: dict[str, Any] = {"db": db.name, "size": db.stat().st_size, "mtime": datetime.fromtimestamp(db.stat().st_mtime).isoformat()}
        try:
            con = sqlite3.connect(db)
            latest = con.execute("SELECT MAX(created_at) FROM trade_journal").fetchone()[0]
            count = con.execute("SELECT COUNT(*) FROM trade_journal").fetchone()[0]
            con.close()
            item.update({"trade_journal_rows": count, "latest_journal": latest})
        except Exception as exc:
            item["error"] = str(exc)
        rows.append(item)
    return rows


def classify(processes: list[dict[str, Any]], mt5: dict[str, Any], findings: list[dict[str, str]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    trade_loops = [
        p for p in processes
        if "mt5_bot trade" in str(p.get("CommandLine", ""))
        and "python" in str(p.get("Name", "")).lower()
    ]
    live_trade_loops = [p for p in trade_loops if "--trade-enabled" in str(p.get("CommandLine", ""))]
    if not processes:
        return "DOWN", ["no suite processes running"]
    if not mt5.get("available"):
        reasons.append("MT5 unavailable")
    if findings:
        reasons.append(f"{len(findings)} recent critical log finding(s)")
    if len(live_trade_loops) not in {0, 3, 12}:
        reasons.append(f"unexpected live trade loop count: {len(live_trade_loops)}")
    if reasons:
        return "DANGEROUS" if any("critical" in r or "MT5 unavailable" in r for r in reasons) else "DEGRADED", reasons
    return "OK", [f"live_trade_loops={len(live_trade_loops)} dry_run_loops={len(trade_loops) - len(live_trade_loops)}"]


def render(payload: dict[str, Any]) -> str:
    lines = [
        "# MT5 Suite Status Report",
        "",
        f"Generated: {payload['generated_at']}",
        f"Since: {payload['since']}",
        f"Status: {payload['status']}",
        f"Reasons: {', '.join(payload['reasons'])}",
        "",
        "## Processes",
        f"- Total suite-related processes: {len(payload['processes'])}",
        f"- Trade loops: {sum(1 for p in payload['processes'] if 'mt5_bot trade' in str(p.get('CommandLine', '')) and 'python' in str(p.get('Name', '')).lower())}",
        f"- Live trade loops: {sum(1 for p in payload['processes'] if 'mt5_bot trade' in str(p.get('CommandLine', '')) and 'python' in str(p.get('Name', '')).lower() and '--trade-enabled' in str(p.get('CommandLine', '')))}",
        f"- Dry-run trade loops: {sum(1 for p in payload['processes'] if 'mt5_bot trade' in str(p.get('CommandLine', '')) and 'python' in str(p.get('Name', '')).lower() and '--trade-enabled' not in str(p.get('CommandLine', '')))}",
        "",
        "## MT5",
    ]
    mt5 = payload["mt5"]
    if mt5.get("available"):
        account = mt5.get("account") or {}
        terminal = mt5.get("terminal") or {}
        lines += [
            f"- Connected: {terminal.get('connected')}",
            f"- Trade allowed: {terminal.get('trade_allowed')}",
            f"- Balance: {account.get('balance')}",
            f"- Equity: {account.get('equity')}",
            f"- Open positions: {len(mt5.get('positions') or [])}",
            "",
            "## PnL By Magic",
        ]
        rows = sorted(mt5.get("by_magic", {}).items(), key=lambda item: float(item[1].get("pnl", 0.0)), reverse=True)
        if not rows:
            lines.append("- No closed PnL deals in window.")
        for magic, row in rows:
            gross_loss = abs(float(row.get("gross_loss", 0.0)))
            pf = (float(row.get("gross_win", 0.0)) / gross_loss) if gross_loss else None
            pf_s = "n/a" if pf is None else f"{pf:.2f}"
            lines.append(
                f"- {row.get('label')} magic={magic}: PnL={float(row.get('pnl', 0.0)):.2f}, "
                f"closed={row.get('closed')}, W={row.get('wins')}, L={row.get('losses')}, "
                f"PF={pf_s}, expectancy={float(row.get('expectancy', 0.0)):.2f}, "
                f"avg_win={float(row.get('avg_win', 0.0)):.2f}, avg_loss={float(row.get('avg_loss', 0.0)):.2f}"
            )
    else:
        lines.append(f"- Unavailable: {mt5.get('error')}")

    lines += ["", "## Recent Critical Logs"]
    if payload["critical_logs"]:
        for item in payload["critical_logs"][:20]:
            lines.append(f"- {item['file']}: {item['line']}")
    else:
        lines.append("- None in inspected window.")
    return "\n".join(lines) + "\n"


def parse_since(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Operational status report for MT5 suite")
    parser.add_argument("--since", default="2026-05-15", help="UTC date/datetime for PnL window")
    parser.add_argument("--log-minutes", type=int, default=180)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    since = parse_since(args.since)
    procs = suite_processes()
    mt5 = mt5_snapshot(since)
    findings = recent_log_findings(args.log_minutes)
    dbs = db_freshness()
    status, reasons = classify(procs, mt5, findings)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "since": since.isoformat(),
        "status": status,
        "reasons": reasons,
        "processes": procs,
        "mt5": mt5,
        "critical_logs": findings,
        "dbs": dbs,
    }
    text = render(payload)
    if args.write:
        REPORT_DIR.mkdir(exist_ok=True)
        (REPORT_DIR / "SUITE_STATUS_REPORT.md").write_text(text, encoding="utf-8")
        (REPORT_DIR / "suite_status_report.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(text)
    return 0 if status in {"OK", "DOWN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
