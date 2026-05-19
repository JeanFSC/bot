from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def _query_one(con: sqlite3.Connection, sql: str, args=()):
    return con.execute(sql, args).fetchone()


def _safe_json(text: str | None) -> dict:
    if not text:
        return {}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def summarize_db(path: Path, since_iso: str, active_position_cutoff_iso: str) -> dict:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        journal = _query_one(
            con,
            """
            SELECT COUNT(*) rows,
                   SUM(CASE WHEN decision='allow' THEN 1 ELSE 0 END) allowed,
                   SUM(CASE WHEN decision='block' THEN 1 ELSE 0 END) blocked,
                   SUM(CASE WHEN execution_status='sent' THEN 1 ELSE 0 END) sent,
                   MAX(created_at) latest
            FROM trade_journal WHERE created_at >= ?
            """,
            (active_position_cutoff_iso,),
        )
        orders = _query_one(
            con,
            """
            SELECT COUNT(*) sent_orders,
                   AVG(slippage_pips) avg_slip,
                   MAX(slippage_pips) max_slip
            FROM orders WHERE phase='send' AND created_at >= ?
            """,
            (since_iso,),
        )
        metrics = _query_one(
            con,
            """
            SELECT COUNT(*) open_tracked,
                   AVG(mfe_pips) avg_mfe,
                   AVG(mae_pips) avg_mae,
                   SUM(current_profit) floating_profit
            FROM position_metrics
            WHERE updated_at >= ?
            """,
            (active_position_cutoff_iso,),
        )
        reasons = con.execute(
            """
            SELECT execution_reason, COUNT(*) n
            FROM trade_journal
            WHERE created_at >= ?
            GROUP BY execution_reason
            ORDER BY n DESC LIMIT 5
            """,
            (since_iso,),
        ).fetchall()
        latest_context = con.execute(
            "SELECT context_json FROM trade_journal WHERE created_at >= ? ORDER BY id DESC LIMIT 1",
            (since_iso,),
        ).fetchone()
        ctx = _safe_json(latest_context[0]) if latest_context else {}
        return {
            "db": path.name,
            "rows": journal["rows"] or 0,
            "allowed": journal["allowed"] or 0,
            "blocked": journal["blocked"] or 0,
            "sent": journal["sent"] or 0,
            "latest": journal["latest"],
            "sent_orders": orders["sent_orders"] or 0,
            "avg_slippage_pips": orders["avg_slip"],
            "max_slippage_pips": orders["max_slip"],
            "open_tracked": metrics["open_tracked"] or 0,
            "avg_mfe_pips": metrics["avg_mfe"],
            "avg_mae_pips": metrics["avg_mae"],
            "floating_profit": metrics["floating_profit"] or 0.0,
            "top_reasons": [(r["execution_reason"], r["n"]) for r in reasons],
            "last_spread_pips": ctx.get("spread_pips"),
            "last_adx": ctx.get("adx"),
            "last_rsi": ctx.get("rsi"),
        }
    finally:
        con.close()


def main() -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    since_iso = since.isoformat()
    active_position_cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
    active_position_cutoff_iso = active_position_cutoff.isoformat()
    rows = [summarize_db(p, since_iso, active_position_cutoff_iso) for p in sorted(DATA.glob("pro*.sqlite"))]
    print(f"Forward report since {since_iso}")
    print(f"active position telemetry since {active_position_cutoff_iso}")
    print("db | rows | sent | orders | active | floating | last spread/adx/rsi | top reasons")
    for r in rows:
        reasons = ", ".join(f"{name}:{n}" for name, n in r["top_reasons"][:3])
        print(
            f"{r['db']} | rows={r['rows']} sent={r['sent']} orders={r['sent_orders']} "
            f"active={r['open_tracked']} float={r['floating_profit']:.2f} "
            f"spread={r['last_spread_pips']} adx={r['last_adx']} rsi={r['last_rsi']} | {reasons}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
