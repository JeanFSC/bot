from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


def analyze_trade_loss(*, symbol: str, pnl: float, context: dict[str, Any]) -> dict[str, Any]:
    causes: list[str] = []
    actions: list[str] = []

    signal_type = str(context.get("signal_type") or context.get("type") or "").upper()
    trend_bias = str(context.get("trend_bias") or context.get("trend") or "").lower()
    adx = _float_or_none(context.get("adx"))
    rsi = _float_or_none(context.get("rsi"))
    spread_pips = _float_or_none(context.get("spread_pips"))
    max_spread_pips = _float_or_none(context.get("max_spread_pips"))
    atr_pips = _float_or_none(context.get("atr_pips") or context.get("atr"))
    session = str(context.get("session") or _session_bucket_from_context(context))

    if (signal_type == "BUY" and trend_bias in {"down", "bearish"}) or (signal_type == "SELL" and trend_bias in {"up", "bullish"}):
        causes.append("trend_conflict")
        actions.append("block_or_reduce_trend_conflict_setup")

    if signal_type == "BUY" and rsi is not None and rsi >= 70:
        causes.append("overbought_buy")
        actions.append("require_rsi_normalization_before_buy")
    if signal_type == "SELL" and rsi is not None and rsi <= 30:
        causes.append("oversold_sell")
        actions.append("require_rsi_normalization_before_sell")

    if adx is not None and adx < 18:
        causes.append("weak_trend")
        actions.append("raise_min_adx_or_avoid_range")

    if spread_pips is not None and max_spread_pips is not None and max_spread_pips > 0:
        if spread_pips >= max_spread_pips * 0.8:
            causes.append("spread_near_limit")
            actions.append("tighten_spread_filter_for_setup")

    if atr_pips is not None and atr_pips <= 0:
        causes.append("invalid_volatility")
        actions.append("block_invalid_atr_context")
    elif atr_pips is not None and atr_pips < 2.0:
        causes.append("low_volatility")
        actions.append("avoid_low_atr_entries")

    if session in {"session_asia", "asia"} and symbol.endswith("JPY"):
        causes.append("session_liquidity_risk")
        actions.append("reduce_jpy_risk_in_asia")

    if not causes:
        causes.append("unclassified_loss")
        actions.append("reduce_risk_until_more_samples")

    abs_loss = abs(float(pnl))
    if abs_loss >= 10:
        severity = "high"
    elif abs_loss >= 3:
        severity = "medium"
    else:
        severity = "low"

    return {
        "severity": severity,
        "causes": sorted(set(causes)),
        "actions": sorted(set(actions)),
        "context": context,
    }


def sync_postmortems(db_path: str | Path) -> int:
    path = Path(db_path)
    if not path.exists():
        return 0
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        _ensure_schema(con)
        rows = con.execute(
            """
            SELECT ticket, created_at, symbol, profit, commission, swap, magic, comment
            FROM deals
            WHERE entry = 1
              AND (COALESCE(profit, 0) + COALESCE(commission, 0) + COALESCE(swap, 0)) < 0
              AND ticket NOT IN (SELECT source_deal_ticket FROM trade_postmortems)
            ORDER BY created_at ASC
            """
        ).fetchall()
        inserted = 0
        for row in rows:
            pnl = float(row["profit"] or 0.0) + float(row["commission"] or 0.0) + float(row["swap"] or 0.0)
            journal = _nearest_journal(con, row["symbol"], int(row["magic"] or 0), str(row["created_at"]))
            context = _journal_context(journal)
            if journal is not None:
                context.setdefault("signal_type", journal["signal_type"])
                context.setdefault("signal_reason", journal["signal_reason"])
                context.setdefault("decision", journal["decision"])
                context.setdefault("execution_reason", journal["execution_reason"])
            analysis = analyze_trade_loss(symbol=row["symbol"], pnl=pnl, context=context)
            con.execute(
                """
                INSERT INTO trade_postmortems (
                    source_deal_ticket, created_at, symbol, magic, pnl, severity,
                    causes_json, actions_json, context_json, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(row["ticket"]),
                    _now(),
                    row["symbol"],
                    int(row["magic"] or 0),
                    pnl,
                    analysis["severity"],
                    json.dumps(analysis["causes"], sort_keys=True),
                    json.dumps(analysis["actions"], sort_keys=True),
                    json.dumps(analysis["context"], sort_keys=True, default=str),
                    _human_note(row["symbol"], pnl, analysis),
                ),
            )
            inserted += 1
        con.commit()
        return inserted
    finally:
        con.close()


def latest_postmortems(db_path: str | Path, limit: int = 10) -> list[dict[str, Any]]:
    path = Path(db_path)
    if not path.exists():
        return []
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    try:
        _ensure_schema(con)
        rows = con.execute(
            """
            SELECT source_deal_ticket, created_at, symbol, magic, pnl, severity,
                   causes_json, actions_json, notes
            FROM trade_postmortems
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [
            {
                "source_deal_ticket": row["source_deal_ticket"],
                "created_at": row["created_at"],
                "symbol": row["symbol"],
                "magic": row["magic"],
                "pnl": row["pnl"],
                "severity": row["severity"],
                "causes": json.loads(row["causes_json"]),
                "actions": json.loads(row["actions_json"]),
                "notes": row["notes"],
            }
            for row in rows
        ]
    finally:
        con.close()


def _ensure_schema(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS trade_postmortems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_deal_ticket INTEGER NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            symbol TEXT NOT NULL,
            magic INTEGER,
            pnl REAL NOT NULL,
            severity TEXT NOT NULL,
            causes_json TEXT NOT NULL,
            actions_json TEXT NOT NULL,
            context_json TEXT NOT NULL,
            notes TEXT NOT NULL
        )
        """
    )
    con.commit()


def _nearest_journal(con: sqlite3.Connection, symbol: str, magic: int, deal_created_at: str):
    return con.execute(
        """
        SELECT *
        FROM trade_journal
        WHERE symbol = ? AND magic = ? AND created_at <= ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (symbol, magic, deal_created_at),
    ).fetchone()


def _journal_context(journal) -> dict[str, Any]:
    if journal is None:
        return {}
    try:
        payload = json.loads(journal["context_json"] or "{}")
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _human_note(symbol: str, pnl: float, analysis: dict[str, Any]) -> str:
    causes = ", ".join(analysis["causes"])
    actions = ", ".join(analysis["actions"])
    return f"{symbol} loss {pnl:.2f}: causes={causes}; corrective_actions={actions}"


def _float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _session_bucket_from_context(context: dict[str, Any]) -> str:
    hour = context.get("hour_utc")
    try:
        h = int(hour)
    except Exception:
        return "unknown"
    if 7 <= h < 12:
        return "session_london"
    if 12 <= h < 17:
        return "session_london_ny"
    if 17 <= h < 22:
        return "session_ny"
    return "session_asia"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_postmortem")
    parser.add_argument("db", nargs="+")
    args = parser.parse_args(argv)
    total = 0
    for db in args.db:
        count = sync_postmortems(db)
        total += count
        print(f"POSTMORTEM_SYNC db={db} inserted={count}")
    print(f"POSTMORTEM_SYNC_TOTAL inserted={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
