from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from mt5_bot.agent_runner import load_agent_config
from mt5_bot.config import load_config
from mt5_bot.postmortem import sync_postmortems


ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "autonomous_trade_review_state.json"
REPORT_DIR = ROOT / "reports" / "autonomous_trade_reviews"
MEMORY_PATH = ROOT / "docs" / "memory" / "autonomous-trade-learning-loop.md"


@dataclass(frozen=True)
class ReviewedTrade:
    source_id: str
    db_path: Path
    ticket: int
    position_id: int | None
    created_at: str
    symbol: str
    magic: int
    side: str
    pnl: float
    volume: float
    entry_price: float | None
    exit_price: float
    sl: float | None
    tp: float | None
    sl_pips: float | None
    tp_pips: float | None
    projected_loss: float | None
    projected_gain: float | None
    projected_cash_rr: float | None
    mfe_pips: float | None
    mae_pips: float | None
    mfe_profit: float | None
    mae_profit: float | None
    comment: str
    causes: list[str]
    lessons: list[str]
    action: str


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Review newly closed autonomous MT5 trades and persist lessons.")
    parser.add_argument("--agent-config", default="config/autonomous_agent.yaml")
    parser.add_argument("--state", default=str(STATE_PATH))
    parser.add_argument("--report-dir", default=str(REPORT_DIR))
    parser.add_argument("--memory", default=str(MEMORY_PATH))
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args(argv)

    state_path = Path(args.state)
    state = _load_state(state_path)
    reviewed_ids = set(state.get("reviewed_source_ids", []))

    agent_config = load_agent_config(ROOT / args.agent_config)
    new_reviews: list[ReviewedTrade] = []
    synced_postmortems = 0
    for cfg_path in agent_config.configs:
        bot_cfg = load_config(ROOT / cfg_path)
        db_path = ROOT / bot_cfg.database_path
        if not db_path.exists():
            continue
        synced_postmortems += sync_postmortems(db_path)
        for review in _review_db(db_path, reviewed_ids, limit=args.limit):
            new_reviews.append(review)
            reviewed_ids.add(review.source_id)

    if new_reviews:
        new_reviews.sort(key=lambda item: item.created_at)
        report_path = _write_report(Path(args.report_dir), new_reviews, synced_postmortems)
        _append_memory(Path(args.memory), new_reviews, report_path)
        state["reviewed_source_ids"] = sorted(reviewed_ids)
        state["last_review_at"] = _now()
        state["last_report"] = str(report_path.relative_to(ROOT))
        _save_state(state_path, state)
        print(f"TRADE_REVIEW new={len(new_reviews)} postmortems={synced_postmortems} report={report_path}")
    else:
        state["last_review_at"] = _now()
        state["reviewed_source_ids"] = sorted(reviewed_ids)
        _save_state(state_path, state)
        print(f"TRADE_REVIEW new=0 postmortems={synced_postmortems}")
    return 0


def _review_db(db_path: Path, reviewed_ids: set[str], *, limit: int) -> list[ReviewedTrade]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT *
            FROM deals
            WHERE entry = 1
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        reviews: list[ReviewedTrade] = []
        for row in rows:
            source_id = f"{db_path.relative_to(ROOT)}:{int(row['ticket'])}"
            if source_id in reviewed_ids:
                continue
            reviews.append(_review_trade(con, db_path, source_id, row))
        return reviews
    finally:
        con.close()


def _review_trade(con: sqlite3.Connection, db_path: Path, source_id: str, row: sqlite3.Row) -> ReviewedTrade:
    raw = _json(row["raw_json"])
    position_id = _int(raw.get("position_id"))
    order_id = _int(row["order_id"])
    magic = _int(row["magic"]) or 0
    pnl = _num(row["profit"]) + _num(row["commission"]) + _num(row["swap"])
    exit_price = _num(row["price"])
    comment = str(row["comment"] or "")
    entry_deal = _find_entry_deal(con, position_id, row["symbol"], magic)
    entry_order_id = _int(entry_deal["order_id"]) if entry_deal is not None else None
    send_order = _find_send_order(con, entry_order_id, row["symbol"])
    journal = _find_execution_journal(con, send_order, row["symbol"], magic)
    journal_context = _json(journal["context_json"]) if journal is not None else {}
    metrics = _find_position_metrics(con, position_id)

    entry_deal_type = _int(entry_deal["deal_type"]) if entry_deal is not None else None
    side = "SELL" if entry_deal_type == 1 else "BUY"
    entry_price = _num_or_none(entry_deal["price"]) if entry_deal is not None else _num_or_none(send_order["result_price"] if send_order is not None else None)
    if entry_price is None and send_order is not None:
        entry_price = _num_or_none(send_order["price"])
    sl = _num_or_none(send_order["sl"] if send_order is not None else None)
    tp = _num_or_none(send_order["tp"] if send_order is not None else None)
    symbol = str(row["symbol"] or "")
    pip = _pip_size(symbol)
    sl_pips = _distance_pips(entry_price, sl, pip) if entry_price is not None and sl is not None else None
    tp_pips = _distance_pips(entry_price, tp, pip) if entry_price is not None and tp is not None else None
    mfe_pips = _num_or_none(metrics["mfe_pips"] if metrics is not None else None)
    mae_pips = _num_or_none(metrics["mae_pips"] if metrics is not None else None)
    mfe_profit = _num_or_none(metrics["mfe_profit"] if metrics is not None else None)
    mae_profit = _num_or_none(metrics["mae_profit"] if metrics is not None else None)

    causes, lessons, action = _classify(
        symbol=symbol,
        pnl=pnl,
        comment=comment,
        sl_pips=sl_pips,
        tp_pips=tp_pips,
        projected_loss=_num_or_none(journal_context.get("projected_loss_usd")),
        projected_gain=_num_or_none(journal_context.get("projected_gain_usd")),
        projected_cash_rr=_num_or_none(journal_context.get("projected_cash_rr")),
        mfe_pips=mfe_pips,
        mfe_profit=mfe_profit,
    )

    return ReviewedTrade(
        source_id=source_id,
        db_path=db_path,
        ticket=int(row["ticket"]),
        position_id=position_id,
        created_at=str(row["created_at"]),
        symbol=symbol,
        magic=magic,
        side=side,
        pnl=pnl,
        volume=_num(row["volume"]),
        entry_price=entry_price,
        exit_price=exit_price,
        sl=sl,
        tp=tp,
        sl_pips=sl_pips,
        tp_pips=tp_pips,
        projected_loss=_num_or_none(journal_context.get("projected_loss_usd")),
        projected_gain=_num_or_none(journal_context.get("projected_gain_usd")),
        projected_cash_rr=_num_or_none(journal_context.get("projected_cash_rr")),
        mfe_pips=mfe_pips,
        mae_pips=mae_pips,
        mfe_profit=mfe_profit,
        mae_profit=mae_profit,
        comment=comment,
        causes=causes,
        lessons=lessons,
        action=action,
    )


def _classify(
    *,
    symbol: str,
    pnl: float,
    comment: str,
    sl_pips: float | None,
    tp_pips: float | None,
    projected_loss: float | None,
    projected_gain: float | None,
    projected_cash_rr: float | None,
    mfe_pips: float | None,
    mfe_profit: float | None,
) -> tuple[list[str], list[str], str]:
    causes: list[str] = []
    lessons: list[str] = []
    action = "record_only"

    if pnl < 0:
        if "[sl" in comment.lower():
            causes.append("closed_by_sl")
        if sl_pips is not None and _is_tight_stop(symbol, sl_pips):
            causes.append("stop_too_tight")
            lessons.append("require_min_sl_or_reduce_lot_when_stop_is_tiny")
            action = "review_sl_floor_or_position_sizing"
        if mfe_profit is not None and mfe_profit > 0:
            causes.append("gave_back_open_profit")
            lessons.append("profit_lock_should_protect_positive_mfe")
            action = "review_profit_lock_threshold"
        if mfe_pips is not None and sl_pips is not None and mfe_pips >= sl_pips:
            causes.append("moved_enough_to_protect")
            lessons.append("move_sl_to_breakeven_or_close_when_mfe_exceeds_initial_risk")
            action = "review_profit_lock_threshold"
        if not causes:
            causes.append("normal_or_unclassified_loss")
            lessons.append("do_not_overfit_single_loss")
    elif pnl > 0:
        if "[tp" in comment.lower():
            causes.append("closed_by_tp")
        else:
            causes.append("profitable_exit")
        lessons.append("preserve_context_if_setup_repeats")
    else:
        causes.append("flat_exit")
        lessons.append("inspect_costs_and_exit_reason")

    return sorted(set(causes)), sorted(set(lessons)), action


def _is_tight_stop(symbol: str, sl_pips: float) -> bool:
    upper = symbol.upper()
    if upper in {"XAUUSD", "GOLD"}:
        return sl_pips < 180
    if "JPY" in upper:
        return sl_pips < 12
    return sl_pips < 8


def _find_entry_deal(con: sqlite3.Connection, position_id: int | None, symbol: str, magic: int):
    if position_id is None:
        return None
    return con.execute(
        """
        SELECT *
        FROM deals
        WHERE entry = 0 AND symbol = ? AND magic = ? AND raw_json LIKE ?
        ORDER BY created_at ASC
        LIMIT 1
        """,
        (symbol, magic, f'%"position_id": {position_id}%'),
    ).fetchone()


def _find_send_order(con: sqlite3.Connection, order_id: int | None, symbol: str):
    row = None
    if order_id is not None:
        row = con.execute(
            """
            SELECT *
            FROM orders
            WHERE phase = 'send' AND symbol = ? AND result_json LIKE ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (symbol, f'%"order": {order_id}%'),
        ).fetchone()
    if row is not None:
        return row
    return None


def _find_execution_journal(con: sqlite3.Connection, send_order, symbol: str, magic: int):
    if send_order is None:
        return None
    created_at = send_order["created_at"]
    return con.execute(
        """
        SELECT *
        FROM trade_journal
        WHERE symbol = ?
          AND magic = ?
          AND execution_status = 'sent'
          AND created_at BETWEEN datetime(?, '-2 minutes') AND datetime(?, '+2 minutes')
        ORDER BY ABS(julianday(created_at) - julianday(?)) ASC
        LIMIT 1
        """,
        (symbol, magic, created_at, created_at, created_at),
    ).fetchone()


def _find_position_metrics(con: sqlite3.Connection, position_id: int | None):
    if position_id is None:
        return None
    return con.execute(
        "SELECT * FROM position_metrics WHERE ticket = ?",
        (position_id,),
    ).fetchone()


def _write_report(report_dir: Path, reviews: list[ReviewedTrade], synced_postmortems: int) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"review_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    lines = [
        "# Autonomous Trade Review",
        "",
        f"Generated: `{_now()}`",
        f"New closed trades reviewed: **{len(reviews)}**",
        f"Postmortems synced: **{synced_postmortems}**",
        "",
    ]
    for review in reviews:
        lines.extend(_trade_lines(review))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _append_memory(memory_path: Path, reviews: list[ReviewedTrade], report_path: Path) -> None:
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    if not memory_path.exists():
        memory_path.write_text("# Autonomous Trade Learning Loop\n\n", encoding="utf-8")
    lines = [
        f"## {_now()}",
        "",
        f"Report: `{report_path.relative_to(ROOT)}`",
        "",
    ]
    for review in reviews:
        lines.append(
            f"- {review.symbol} {review.side} ticket={review.ticket} pnl={review.pnl:.2f} "
            f"causes={','.join(review.causes)} action={review.action}"
        )
    lines.append("")
    with memory_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _trade_lines(review: ReviewedTrade) -> list[str]:
    return [
        f"## {review.symbol} {review.side} ticket `{review.ticket}`",
        "",
        f"- Source: `{review.source_id}`",
        f"- Closed at: `{review.created_at}`",
        f"- PnL: **{review.pnl:.2f}**",
        f"- Volume: `{review.volume}`",
        f"- Entry/exit: `{_fmt(review.entry_price)}` -> `{review.exit_price:.5f}`",
        f"- SL/TP: `{_fmt(review.sl)}` / `{_fmt(review.tp)}`",
        f"- SL/TP distance: `{_fmt(review.sl_pips)} pips` / `{_fmt(review.tp_pips)} pips`",
        f"- Projected SL/TP cash: `-{_fmt(review.projected_loss)}` / `+{_fmt(review.projected_gain)}`",
        f"- Projected cash R:R: `{_fmt(review.projected_cash_rr)}`",
        f"- MFE/MAE: `{_fmt(review.mfe_pips)} pips` / `{_fmt(review.mae_pips)} pips`",
        f"- MFE/MAE profit: `{_fmt(review.mfe_profit)}` / `{_fmt(review.mae_profit)}`",
        f"- Broker comment: `{review.comment}`",
        f"- Causes: `{', '.join(review.causes)}`",
        f"- Lessons: `{', '.join(review.lessons)}`",
        f"- Suggested action: `{review.action}`",
        "",
    ]


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"reviewed_source_ids": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"reviewed_source_ids": []}
    except Exception:
        return {"reviewed_source_ids": []}


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _distance_pips(a: float | None, b: float | None, pip: float) -> float | None:
    if a is None or b is None or pip <= 0:
        return None
    return abs(a - b) / pip


def _pip_size(symbol: str) -> float:
    upper = symbol.upper()
    if upper in {"XAUUSD", "GOLD"}:
        return 0.01
    if "JPY" in upper:
        return 0.01
    return 0.0001


def _int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


def _num(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _num_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}" if abs(value) >= 1 else f"{value:.5f}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
