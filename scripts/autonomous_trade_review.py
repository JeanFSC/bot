from __future__ import annotations

import argparse
import json
import os
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
UPDATE_QUEUE_DIR = ROOT / "reports" / "pending_update_proposals"


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
    mfe_capture_ratio: float | None
    winner_quality: str
    scale_verdict: str
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
    parser.add_argument("--update-queue-dir", default=str(UPDATE_QUEUE_DIR))
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--lock-stale-minutes", type=float, default=45.0)
    args = parser.parse_args(argv)

    state_path = Path(args.state)
    lock_path = state_path.with_suffix(state_path.suffix + ".lock")
    if not _acquire_lock(lock_path, stale_minutes=args.lock_stale_minutes):
        print(f"TRADE_REVIEW skipped=lock_active lock={lock_path}")
        return 0

    try:
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
            proposal_path = _write_update_proposals(Path(args.update_queue_dir), new_reviews, report_path)
            _append_memory(Path(args.memory), new_reviews, report_path)
            state["reviewed_source_ids"] = sorted(reviewed_ids)
            state["last_review_at"] = _now()
            state["last_report"] = str(report_path.relative_to(ROOT))
            state["last_update_proposals"] = str(proposal_path.relative_to(ROOT)) if proposal_path else None
            _save_state(state_path, state)
            proposal_text = f" proposals={proposal_path}" if proposal_path else " proposals=0"
            print(f"TRADE_REVIEW new={len(new_reviews)} postmortems={synced_postmortems} report={report_path}{proposal_text}")
        else:
            state["last_review_at"] = _now()
            state["reviewed_source_ids"] = sorted(reviewed_ids)
            _save_state(state_path, state)
            print(f"TRADE_REVIEW new=0 postmortems={synced_postmortems}")
        return 0
    finally:
        _release_lock(lock_path)


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
    mfe_capture_ratio, winner_quality, scale_verdict = _winner_diagnostics(
        pnl=pnl,
        mfe_pips=mfe_pips,
        mae_pips=mae_pips,
        mfe_profit=mfe_profit,
    )

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
    if winner_quality == "winner_left_money_on_table":
        causes.append("low_mfe_capture")
        lessons.append("review_runner_or_winner_scaling_for_clean_winner")
        if action == "record_only":
            action = "review_winner_runner_or_scale_logic"
    if scale_verdict == "scale_candidate_clean_winner":
        lessons.append("setup_can_be_candidate_for_controlled_addon_after_confirmation")
    elif scale_verdict == "no_scale_survived_winner":
        lessons.append("do_not_scale_survived_winner_with_high_mae")

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
        mfe_capture_ratio=mfe_capture_ratio,
        winner_quality=winner_quality,
        scale_verdict=scale_verdict,
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


def _winner_diagnostics(
    *,
    pnl: float,
    mfe_pips: float | None,
    mae_pips: float | None,
    mfe_profit: float | None,
) -> tuple[float | None, str, str]:
    if pnl <= 0:
        return None, "not_winner", "not_applicable"

    capture_ratio = None
    if mfe_profit is not None and mfe_profit > 0:
        capture_ratio = max(0.0, min(1.0, pnl / mfe_profit))

    if mfe_pips is None or mfe_pips <= 0:
        return capture_ratio, "winner_without_mfe_data", "no_scale_missing_mfe"

    adverse_ratio = abs(min(0.0, mae_pips or 0.0)) / mfe_pips
    left_money = capture_ratio is not None and capture_ratio < 0.65
    if adverse_ratio <= 0.35:
        quality = "winner_left_money_on_table" if left_money else "clean_winner"
        verdict = "scale_candidate_clean_winner"
    else:
        quality = "survived_winner"
        verdict = "no_scale_survived_winner"
    return capture_ratio, quality, verdict


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


def _write_update_proposals(
    queue_dir: Path,
    reviews: list[ReviewedTrade],
    report_path: Path,
) -> Path | None:
    actionable = [review for review in reviews if review.action != "record_only"]
    if not actionable:
        return None

    queue_dir.mkdir(parents=True, exist_ok=True)
    created_at = _now()
    payload = {
        "created_at": created_at,
        "source_report": str(report_path.relative_to(ROOT)),
        "status": "pending_review",
        "activation_gate": "stage_and_test_only; activate runtime changes only in clean MT5 window with positions=0 and orders=0",
        "proposals": [_update_proposal(review) for review in actionable],
    }
    path = queue_dir / f"proposal_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _update_proposal(review: ReviewedTrade) -> dict[str, Any]:
    return {
        "ticket": review.ticket,
        "symbol": review.symbol,
        "magic": review.magic,
        "side": review.side,
        "pnl": round(review.pnl, 2),
        "action": review.action,
        "causes": review.causes,
        "lessons": review.lessons,
        "winner_quality": review.winner_quality,
        "scale_verdict": review.scale_verdict,
        "mfe_capture_ratio": review.mfe_capture_ratio,
        "projected_cash_rr": review.projected_cash_rr,
        "recommendation": _proposal_recommendation(review),
        "risk_gate": "no live/demo runtime relaunch unless MT5 has zero positions and zero pending orders",
    }


def _proposal_recommendation(review: ReviewedTrade) -> str:
    if review.action == "review_winner_runner_or_scale_logic":
        return "Review winner scaling/profit-lock thresholds for this symbol; require clean MFE, low MAE, fresh portfolio heat, and addon risk cap before any config change."
    if review.action == "review_sl_floor_or_position_sizing":
        return "Review minimum SL floor and position sizing for this symbol; prefer lower size over tight stops when broker/ATR conditions are poor."
    if review.action == "review_profit_lock_threshold":
        return "Review profit-lock trigger and retrace buffer; protect positive MFE without forcing premature exits in normal noise."
    return "Review manually; no automatic config change is approved by this proposal."


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
        f"- MFE capture ratio: `{_fmt(review.mfe_capture_ratio)}`",
        f"- Winner quality: `{review.winner_quality}`",
        f"- Scale verdict: `{review.scale_verdict}`",
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


def _acquire_lock(path: Path, *, stale_minutes: float) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if not _lock_is_stale(path, stale_minutes=stale_minutes):
            return False
        path.unlink(missing_ok=True)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump({"pid": os.getpid(), "created_at": _now()}, handle)
        handle.write("\n")
    return True


def _lock_is_stale(path: Path, *, stale_minutes: float) -> bool:
    try:
        age_seconds = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
    except OSError:
        return True
    return age_seconds > max(1.0, stale_minutes * 60.0)


def _release_lock(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


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
