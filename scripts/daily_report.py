from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"


def q(con, sql, args=()):
    try:
        return con.execute(sql, args).fetchone()
    except sqlite3.Error:
        return None


def report_db(path: Path, since: str) -> dict:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        pnl = q(con, "SELECT COALESCE(SUM(COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0)),0) pnl, COUNT(*) deals FROM deals WHERE created_at >= ?", (since,))
        deal_rows = con.execute(
            "SELECT ticket, COALESCE(profit,0)+COALESCE(commission,0)+COALESCE(swap,0) pnl FROM deals WHERE created_at >= ?",
            (since,),
        ).fetchall()
        sent = q(con, "SELECT COUNT(*) n, AVG(slippage_pips) slip FROM orders WHERE phase='send' AND created_at >= ?", (since,))
        missing_deal_rows = con.execute(
            """
            SELECT id,
                   CAST(json_extract(result_json, '$.deal') AS INTEGER) deal_ticket
            FROM orders
            WHERE phase='send'
              AND created_at >= ?
              AND retcode IN (10008, 10009)
              AND CAST(COALESCE(json_extract(result_json, '$.deal'), 0) AS INTEGER) > 0
              AND CAST(json_extract(result_json, '$.deal') AS INTEGER) NOT IN (
                  SELECT ticket FROM deals
              )
            """,
            (since,),
        ).fetchall()
        blocks = q(con, "SELECT COUNT(*) n FROM trade_journal WHERE created_at >= ? AND execution_status='rejected'", (since,))
        latest = q(con, "SELECT symbol, execution_reason, context_json FROM trade_journal ORDER BY id DESC LIMIT 1")
        return {
            "db": path.name,
            "pnl": float(pnl["pnl"] if pnl else 0.0),
            "deals": int(pnl["deals"] if pnl else 0),
            "sent_orders": int(sent["n"] if sent else 0),
            "avg_slippage_pips": float(sent["slip"]) if sent and sent["slip"] is not None else None,
            "rejections": int(blocks["n"] if blocks else 0),
            "missing_deal_sync": len(missing_deal_rows),
            "missing_deal_tickets": [int(r["deal_ticket"]) for r in missing_deal_rows],
            "latest_symbol": latest["symbol"] if latest else None,
            "latest_reason": latest["execution_reason"] if latest else None,
            "_deals": [{"ticket": int(r["ticket"]), "pnl": float(r["pnl"])} for r in deal_rows],
        }
    finally:
        con.close()


def main() -> int:
    since_dt = datetime.now(timezone.utc) - timedelta(hours=24)
    since = since_dt.isoformat()
    rows = [report_db(p, since) for p in sorted(DATA.glob("pro*.sqlite"))]
    unique_deals = {}
    duplicate_deals = 0
    duplicate_sources = {}
    for row in rows:
        for deal in row.pop("_deals", []):
            ticket = deal["ticket"]
            if ticket in unique_deals:
                duplicate_deals += 1
                duplicate_sources.setdefault(ticket, []).append(row["db"])
                continue
            duplicate_sources.setdefault(ticket, [row["db"]])
            unique_deals[ticket] = deal["pnl"]
    total_pnl = sum(unique_deals.values())
    total_orders = sum(r["sent_orders"] for r in rows)
    total_reject = sum(r["rejections"] for r in rows)
    total_missing_sync = sum(r["missing_deal_sync"] for r in rows)
    lines = ["# MT5 Daily Forward Report", "", f"Since: `{since}`", "", f"Total PnL: **{total_pnl:.2f}**", f"Unique deal tickets: **{len(unique_deals)}**", f"Duplicate deal rows ignored in total: **{duplicate_deals}**", f"Missing synced deal tickets: **{total_missing_sync}**", f"Sent orders: **{total_orders}**", f"Rejected attempts: **{total_reject}**", "", "| DB | PnL | Deals | Orders | Missing sync | Avg slip | Rejections | Latest reason |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in rows:
        slip = f"{r['avg_slippage_pips']:.2f}" if r["avg_slippage_pips"] is not None else "n/a"
        lines.append(f"| {r['db']} | {r['pnl']:.2f} | {r['deals']} | {r['sent_orders']} | {r['missing_deal_sync']} | {slip} | {r['rejections']} | {r['latest_reason']} |")
    duplicate_details = {ticket: dbs for ticket, dbs in duplicate_sources.items() if len(dbs) > 1}
    if duplicate_details:
        lines.extend(["", "## Duplicate Deal Tickets", ""])
        for ticket, dbs in sorted(duplicate_details.items()):
            lines.append(f"- `{ticket}` in {', '.join(dbs)}")
    missing_rows = [r for r in rows if r["missing_deal_sync"]]
    if missing_rows:
        lines.extend(["", "## Missing Deal Sync", ""])
        for r in missing_rows:
            tickets = ", ".join(f"`{ticket}`" for ticket in r["missing_deal_tickets"])
            lines.append(f"- `{r['db']}` missing deal tickets: {tickets}")
    text = "\n".join(lines) + "\n"
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "DAILY_FORWARD_REPORT.md").write_text(text, encoding="utf-8")
    (REPORTS / "daily_forward_report.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(text)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
