from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SUCCESS_RETCODES = {0, 10008, 10009}


@dataclass(frozen=True)
class ClosedDealAudit:
    db: str
    symbol: str
    magic: int | None
    ticket: int
    position_id: int | None
    opened_at: str | None
    closed_at: str
    volume: float
    pnl: float
    broker_comment: str
    exit_reason: str
    evidence: str
    mfe_pips: float | None = None
    mae_pips: float | None = None
    mfe_profit: float | None = None
    mae_profit: float | None = None


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def classify_broker_exit(comment: str, pnl: float) -> tuple[str | None, str]:
    text = comment.lower()
    if "[tp" in text or " tp " in f" {text} ":
        return "take_profit", "broker_comment_tp"
    if "[sl" in text or " sl " in f" {text} ":
        if pnl < -0.05:
            return "sl_loss", "broker_comment_sl_negative_pnl"
        if abs(pnl) <= 0.05:
            return "breakeven_sl", "broker_comment_sl_near_zero_pnl"
        return "protective_sl_profit", "broker_comment_sl_positive_pnl"
    if text.startswith("mt5bot_ord"):
        return "bot_client_close_original_comment", f"deal_comment={comment}"
    if text.startswith("mt5bot_close"):
        return "bot_close_unknown", f"deal_comment={comment}"
    return None, ""


def classify_bot_order(request: dict[str, Any], journal_reason: str | None) -> tuple[str, str]:
    comment = str(request.get("comment") or "").lower()
    if "partial" in comment:
        return "partial_close", f"order_comment={comment}"
    if journal_reason:
        reason = journal_reason.lower()
        if "opposite" in reason or "reverse" in reason:
            return "reverse_signal", f"journal_reason={journal_reason}"
        if "profit_target" in reason:
            return "profit_target", f"journal_reason={journal_reason}"
    if "close" in comment:
        return "bot_close_unknown", f"order_comment={comment}"
    return "manual_or_external", f"order_comment={comment or 'n/a'}"


def nearest_journal_reason(rows: list[sqlite3.Row], when: datetime | None) -> str | None:
    if when is None:
        return None
    best: tuple[float, str] | None = None
    for row in rows:
        created = parse_time(row["created_at"])
        if created is None:
            continue
        delta = abs((created - when).total_seconds())
        if delta > 180:
            continue
        reason = str(row["execution_reason"] or "")
        status = str(row["execution_status"] or "")
        if not reason and not status:
            continue
        candidate = f"{status}:{reason}" if status else reason
        if best is None or delta < best[0]:
            best = (delta, candidate)
    return best[1] if best else None


def successful_orders(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT created_at, order_type, volume, comment, request_json, result_json, retcode
        FROM orders
        WHERE phase = 'send'
        ORDER BY created_at
        """
    ).fetchall()
    orders: list[dict[str, Any]] = []
    for row in rows:
        retcode = row["retcode"]
        if retcode is not None and int(retcode) not in SUCCESS_RETCODES:
            continue
        request = load_json(row["request_json"])
        result = load_json(row["result_json"])
        orders.append({
            "created_at": row["created_at"],
            "created": parse_time(row["created_at"]),
            "request": request,
            "result": result,
            "result_order": result.get("order"),
            "request_position": request.get("position"),
        })
    return orders


def match_close_order(
    orders: list[dict[str, Any]],
    *,
    position_id: int | None,
    order_id: int | None,
    closed_at: datetime | None,
) -> dict[str, Any] | None:
    best: tuple[float, dict[str, Any]] | None = None
    for order in orders:
        request_position = order.get("request_position")
        matches_position = position_id is not None and request_position is not None and int(request_position) == int(position_id)
        if not matches_position:
            continue
        created = order.get("created")
        delta = abs((created - closed_at).total_seconds()) if created and closed_at else 0.0
        if best is None or delta < best[0]:
            best = (delta, order)
    return best[1] if best else None


def position_metrics_history(connection: sqlite3.Connection, position_id: int | None) -> dict[str, Any] | None:
    if position_id is None:
        return None
    try:
        row = connection.execute(
            """
            SELECT mfe_pips, mae_pips, mfe_profit, mae_profit
            FROM position_metrics_history
            WHERE ticket = ?
            ORDER BY archived_at DESC
            LIMIT 1
            """,
            (position_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    return dict(row) if row is not None else None


def audit_db(path: Path, since: datetime | None = None) -> list[ClosedDealAudit]:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        deals = connection.execute("SELECT * FROM deals ORDER BY created_at").fetchall()
        entries_by_position: dict[int, sqlite3.Row] = {}
        closed_deals: list[sqlite3.Row] = []
        for row in deals:
            raw = load_json(row["raw_json"])
            position_id = raw.get("position_id")
            if position_id is None:
                continue
            if int(row["entry"] or 0) == 0:
                entries_by_position[int(position_id)] = row
            elif int(row["entry"] or 0) == 1:
                closed = parse_time(row["created_at"])
                if since is None or (closed is not None and closed >= since):
                    closed_deals.append(row)

        orders = successful_orders(connection)
        journal_rows = connection.execute(
            """
            SELECT created_at, execution_status, execution_reason
            FROM trade_journal
            WHERE execution_status IS NOT NULL
            ORDER BY created_at
            """
        ).fetchall()

        audits: list[ClosedDealAudit] = []
        for row in closed_deals:
            raw = load_json(row["raw_json"])
            position_id = int(raw["position_id"]) if raw.get("position_id") is not None else None
            opened = entries_by_position.get(position_id) if position_id is not None else None
            closed_at = parse_time(row["created_at"])
            pnl = float(row["profit"] or 0.0)
            comment = str(row["comment"] or "")
            reason, evidence = classify_broker_exit(comment, pnl)
            if reason is None:
                close_order = match_close_order(
                    orders,
                    position_id=position_id,
                    order_id=int(row["order_id"]) if row["order_id"] is not None else None,
                    closed_at=closed_at,
                )
                if close_order is None:
                    reason, evidence = "manual_or_external", "no_matching_bot_close_order"
                else:
                    journal_reason = nearest_journal_reason(journal_rows, close_order.get("created"))
                    reason, evidence = classify_bot_order(close_order["request"], journal_reason)
            metrics = position_metrics_history(connection, position_id)
            audits.append(
                ClosedDealAudit(
                    db=path.name,
                    symbol=str(row["symbol"] or ""),
                    magic=int(row["magic"]) if row["magic"] is not None else None,
                    ticket=int(row["ticket"]),
                    position_id=position_id,
                    opened_at=str(opened["created_at"]) if opened else None,
                    closed_at=str(row["created_at"]),
                    volume=float(row["volume"] or 0.0),
                    pnl=pnl,
                    broker_comment=comment,
                    exit_reason=reason,
                    evidence=evidence,
                    mfe_pips=float(metrics["mfe_pips"]) if metrics and metrics.get("mfe_pips") is not None else None,
                    mae_pips=float(metrics["mae_pips"]) if metrics and metrics.get("mae_pips") is not None else None,
                    mfe_profit=float(metrics["mfe_profit"]) if metrics and metrics.get("mfe_profit") is not None else None,
                    mae_profit=float(metrics["mae_profit"]) if metrics and metrics.get("mae_profit") is not None else None,
                )
            )
        return audits
    finally:
        connection.close()


def profit_factor(values: list[float]) -> float | None:
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    if gross_loss <= 0:
        return None if gross_profit <= 0 else float("inf")
    return gross_profit / gross_loss


def summarize(audits: list[ClosedDealAudit], key: str) -> list[tuple[str, dict[str, Any]]]:
    grouped: dict[str, list[ClosedDealAudit]] = defaultdict(list)
    for audit in audits:
        grouped[getattr(audit, key)].append(audit)
    rows: list[tuple[str, dict[str, Any]]] = []
    for name, items in grouped.items():
        pnls = [item.pnl for item in items]
        wins = [value for value in pnls if value > 0]
        losses = [value for value in pnls if value < 0]
        rows.append((
            str(name),
            {
                "trades": len(items),
                "wins": len(wins),
                "losses": len(losses),
                "net": sum(pnls),
                "pf": profit_factor(pnls),
                "avg_win": sum(wins) / len(wins) if wins else 0.0,
                "avg_loss": sum(losses) / len(losses) if losses else 0.0,
            },
        ))
    rows.sort(key=lambda item: (item[1]["net"], item[1]["trades"]))
    return rows


def fmt_money(value: float) -> str:
    return f"{value:+.2f}"


def fmt_pf(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value == float("inf"):
        return "inf"
    return f"{value:.2f}"


def fmt_optional(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1f}"


def render_report(audits: list[ClosedDealAudit], since: datetime | None) -> str:
    metric_rows = sum(1 for audit in audits if audit.mfe_pips is not None or audit.mae_pips is not None)
    lines = [
        "# MT5 Exit Reason Audit",
        "",
        f"- Created at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Since: `{since.isoformat() if since else 'all recorded closes'}`",
        f"- Closed deal rows: `{len(audits)}`",
        f"- Closed rows with archived MFE/MAE: `{metric_rows}`",
        "- Note: older DB rows may lack archived MFE/MAE; new closes should retain it through `position_metrics_history`.",
        "",
        "## Summary By Exit Reason",
        "",
        "| exit_reason | trades | W/L | net | PF | avg_win | avg_loss |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, row in summarize(audits, "exit_reason"):
        lines.append(
            f"| {name} | {row['trades']} | {row['wins']}/{row['losses']} | "
            f"{fmt_money(row['net'])} | {fmt_pf(row['pf'])} | {fmt_money(row['avg_win'])} | {fmt_money(row['avg_loss'])} |"
        )
    lines.extend([
        "",
        "## Summary By Symbol",
        "",
        "| symbol | trades | W/L | net | PF | avg_win | avg_loss |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for name, row in summarize(audits, "symbol"):
        lines.append(
            f"| {name} | {row['trades']} | {row['wins']}/{row['losses']} | "
            f"{fmt_money(row['net'])} | {fmt_pf(row['pf'])} | {fmt_money(row['avg_win'])} | {fmt_money(row['avg_loss'])} |"
        )
    lines.extend([
        "",
        "## Closed Deals",
        "",
        "| closed_at | symbol | ticket | pnl | exit_reason | MFE pips | MAE pips | evidence | comment |",
        "| --- | --- | ---: | ---: | --- | ---: | ---: | --- | --- |",
    ])
    for audit in sorted(audits, key=lambda item: item.closed_at):
        lines.append(
            f"| {audit.closed_at} | {audit.symbol} | {audit.ticket} | {fmt_money(audit.pnl)} | "
            f"{audit.exit_reason} | {fmt_optional(audit.mfe_pips)} | {fmt_optional(audit.mae_pips)} | "
            f"{audit.evidence} | {audit.broker_comment or 'n/a'} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--since", default=None, help="UTC ISO timestamp, for example 2026-07-03T00:00:00+00:00")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    since = parse_time(args.since) if args.since else None
    audits: list[ClosedDealAudit] = []
    for path in sorted(Path(args.data_dir).glob("pro_*.sqlite")):
        audits.extend(audit_db(path, since=since))
    report = render_report(audits, since)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
