from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from mt5_bot.strategy import Signal


def _json_default(value):
    if hasattr(value, "_asdict"):
        return value._asdict()
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class BotStorage:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=30.0)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.execute("PRAGMA busy_timeout=30000")
        self.initialize()

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS account_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                balance REAL,
                equity REAL,
                margin REAL,
                margin_free REAL,
                raw_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                price REAL,
                fast_ema REAL,
                slow_ema REAL,
                rsi REAL,
                atr REAL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                symbol TEXT,
                action INTEGER,
                order_type INTEGER,
                volume REAL,
                price REAL,
                sl REAL,
                tp REAL,
                retcode INTEGER,
                comment TEXT,
                phase TEXT NOT NULL,
                request_json TEXT NOT NULL,
                result_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                bid REAL,
                ask REAL,
                spread_pips REAL
            );

            CREATE TABLE IF NOT EXISTS position_metrics (
                ticket INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                magic INTEGER,
                opened_at TEXT,
                updated_at TEXT NOT NULL,
                side INTEGER,
                volume REAL,
                entry_price REAL,
                current_price REAL,
                current_profit REAL,
                current_pips REAL,
                mfe_pips REAL,
                mae_pips REAL,
                mfe_profit REAL,
                mae_profit REAL
            );

            CREATE TABLE IF NOT EXISTS position_metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                archived_at TEXT NOT NULL,
                ticket INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                magic INTEGER,
                opened_at TEXT,
                updated_at TEXT NOT NULL,
                side INTEGER,
                volume REAL,
                entry_price REAL,
                current_price REAL,
                current_profit REAL,
                current_pips REAL,
                mfe_pips REAL,
                mae_pips REAL,
                mfe_profit REAL,
                mae_profit REAL
            );

            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket INTEGER NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                order_id INTEGER,
                symbol TEXT,
                deal_type INTEGER,
                entry INTEGER,
                volume REAL,
                price REAL,
                profit REAL,
                commission REAL,
                swap REAL,
                magic INTEGER,
                comment TEXT,
                raw_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trade_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                magic INTEGER,
                signal_type TEXT NOT NULL,
                signal_reason TEXT NOT NULL,
                decision TEXT NOT NULL,
                execution_status TEXT,
                execution_reason TEXT,
                risk_pct REAL,
                risk_multiplier REAL,
                portfolio_reason TEXT,
                rr REAL,
                context_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runtime_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                level TEXT NOT NULL,
                symbol TEXT,
                magic INTEGER,
                event_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                context_json TEXT NOT NULL
            );
            """
        )
        self._ensure_order_columns()
        self.connection.commit()

    def _ensure_order_columns(self) -> None:
        """Lightweight migrations for older SQLite files."""
        existing = {row[1] for row in self.connection.execute("PRAGMA table_info(orders)")}
        additions = {
            "result_price": "REAL",
            "slippage_pips": "REAL",
        }
        for name, ddl_type in additions.items():
            if name not in existing:
                self.connection.execute(f"ALTER TABLE orders ADD COLUMN {name} {ddl_type}")

    def close(self) -> None:
        self.connection.close()

    def record_account(self, account_info) -> None:
        payload = account_info._asdict() if hasattr(account_info, "_asdict") else dict(account_info)
        self.connection.execute(
            """
            INSERT INTO account_snapshots (created_at, balance, equity, margin, margin_free, raw_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                payload.get("balance"),
                payload.get("equity"),
                payload.get("margin"),
                payload.get("margin_free"),
                json.dumps(payload, default=_json_default),
            ),
        )
        self.connection.commit()

    def record_runtime_event(
        self,
        event_type: str,
        reason: str,
        *,
        symbol: str | None = None,
        magic: int | None = None,
        level: str = "info",
        context: dict[str, Any] | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO runtime_events (
                created_at, level, symbol, magic, event_type, reason, context_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                level,
                symbol,
                magic,
                event_type,
                reason,
                json.dumps(context or {}, default=_json_default),
            ),
        )
        self.connection.commit()

    def runtime_event_exists(
        self,
        event_type: str,
        reason: str,
        *,
        symbol: str | None = None,
        magic: int | None = None,
    ) -> bool:
        clauses = ["event_type = ?", "reason = ?"]
        params: list[Any] = [event_type, reason]
        if symbol is not None:
            clauses.append("symbol = ?")
            params.append(symbol)
        if magic is not None:
            clauses.append("magic = ?")
            params.append(magic)
        row = self.connection.execute(
            f"SELECT 1 FROM runtime_events WHERE {' AND '.join(clauses)} LIMIT 1",
            params,
        ).fetchone()
        return row is not None

    def record_signal(self, symbol: str, signal: Signal) -> None:
        self.connection.execute(
            """
            INSERT INTO signals (created_at, symbol, signal_type, reason, price, fast_ema, slow_ema, rsi, atr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (_now(), symbol, signal.type.value, signal.reason, signal.price, signal.fast_ema, signal.slow_ema, signal.rsi, signal.atr),
        )
        self.connection.commit()

    def record_market_metrics(self, symbol: str, bid: float, ask: float, spread_pips: float) -> None:
        self.connection.execute(
            """
            INSERT INTO market_metrics (created_at, symbol, bid, ask, spread_pips)
            VALUES (?, ?, ?, ?, ?)
            """,
            (_now(), symbol, bid, ask, spread_pips),
        )
        self.connection.commit()

    def record_order_request(self, request: dict[str, Any], check_result) -> None:
        self._record_order(request, check_result, "check")

    def record_order_result(self, request: dict[str, Any], send_result, symbol_info=None) -> None:
        self._record_order(request, send_result, "send", symbol_info=symbol_info)

    def record_trade_journal(
        self,
        symbol: str,
        magic: int,
        signal: Signal,
        decision: str,
        execution_status: str | None = None,
        execution_reason: str | None = None,
        risk_pct: float | None = None,
        risk_multiplier: float | None = None,
        portfolio_reason: str | None = None,
        rr: float | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Append an audit row for every actionable signal, block, or order."""
        self.connection.execute(
            """
            INSERT INTO trade_journal (
                created_at, symbol, magic, signal_type, signal_reason, decision,
                execution_status, execution_reason, risk_pct, risk_multiplier,
                portfolio_reason, rr, context_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(), symbol, magic, signal.type.value, signal.reason, decision,
                execution_status, execution_reason, risk_pct, risk_multiplier,
                portfolio_reason, rr, json.dumps(context or {}, default=_json_default),
            ),
        )
        self.connection.commit()

    def record_deals(self, deals) -> int:
        inserted = 0
        for deal in deals:
            payload = deal._asdict() if hasattr(deal, "_asdict") else dict(deal)
            ticket = payload.get("ticket")
            if ticket is None:
                continue
            created_at = _time_from_epoch(payload.get("time"))
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO deals (
                    ticket, created_at, order_id, symbol, deal_type, entry, volume,
                    price, profit, commission, swap, magic, comment, raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(ticket),
                    created_at,
                    payload.get("order"),
                    payload.get("symbol"),
                    payload.get("type"),
                    payload.get("entry"),
                    payload.get("volume"),
                    payload.get("price"),
                    payload.get("profit"),
                    payload.get("commission"),
                    payload.get("swap"),
                    payload.get("magic"),
                    payload.get("comment"),
                    json.dumps(payload, default=_json_default),
                ),
            )
            inserted += cursor.rowcount
        self.connection.commit()
        return inserted

    def _record_order(self, request: dict[str, Any], result, phase: str, symbol_info=None) -> None:
        result_payload = result._asdict() if hasattr(result, "_asdict") else {"result": str(result)}
        result_price = result_payload.get("price")
        slippage_pips = None
        try:
            if result_price is not None and request.get("price") is not None and symbol_info is not None:
                fill = float(result_price)
                requested = float(request.get("price"))
                if fill > 0 and requested > 0:
                    pip = _pip_size_from_symbol_info(symbol_info)
                    if pip > 0:
                        slippage_pips = (fill - requested) / pip
                        if int(request.get("type", -1)) == 1:  # sell benefits when filled lower? Track signed cost from requested direction.
                            slippage_pips *= -1
        except Exception:
            slippage_pips = None
        self.connection.execute(
            """
            INSERT INTO orders (
                created_at, symbol, action, order_type, volume, price, sl, tp,
                retcode, comment, phase, request_json, result_json, result_price, slippage_pips
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _now(),
                request.get("symbol"),
                request.get("action"),
                request.get("type"),
                request.get("volume"),
                request.get("price"),
                request.get("sl"),
                request.get("tp"),
                result_payload.get("retcode"),
                result_payload.get("comment"),
                phase,
                json.dumps(request, default=_json_default),
                json.dumps(result_payload, default=_json_default),
                result_price,
                slippage_pips,
            ),
        )
        self.connection.commit()

    def record_position_metrics(self, position, current_price: float, current_pips: float) -> None:
        payload = position._asdict() if hasattr(position, "_asdict") else getattr(position, "__dict__", {})
        ticket = int(payload.get("ticket"))
        profit = float(payload.get("profit", 0.0) or 0.0)
        previous = self.connection.execute(
            "SELECT mfe_pips, mae_pips, mfe_profit, mae_profit FROM position_metrics WHERE ticket = ?",
            (ticket,),
        ).fetchone()
        if previous:
            mfe_pips = max(float(previous[0]), current_pips)
            mae_pips = min(float(previous[1]), current_pips)
            mfe_profit = max(float(previous[2]), profit)
            mae_profit = min(float(previous[3]), profit)
        else:
            mfe_pips = mae_pips = current_pips
            mfe_profit = mae_profit = profit
        opened_at = _time_from_epoch(payload.get("time")) if payload.get("time") is not None else None
        self.connection.execute(
            """
            INSERT INTO position_metrics (
                ticket, symbol, magic, opened_at, updated_at, side, volume,
                entry_price, current_price, current_profit, current_pips,
                mfe_pips, mae_pips, mfe_profit, mae_profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticket) DO UPDATE SET
                updated_at=excluded.updated_at,
                current_price=excluded.current_price,
                current_profit=excluded.current_profit,
                current_pips=excluded.current_pips,
                mfe_pips=excluded.mfe_pips,
                mae_pips=excluded.mae_pips,
                mfe_profit=excluded.mfe_profit,
                mae_profit=excluded.mae_profit
            """,
            (
                ticket, payload.get("symbol"), payload.get("magic"), opened_at, _now(),
                payload.get("type"), payload.get("volume"), payload.get("price_open"),
                current_price, profit, current_pips, mfe_pips, mae_pips, mfe_profit, mae_profit,
            ),
        )
        self.connection.commit()

    def get_position_metrics(self, ticket: int) -> dict[str, Any] | None:
        row = self.connection.execute(
            """
            SELECT ticket, symbol, magic, opened_at, updated_at, side, volume,
                   entry_price, current_price, current_profit, current_pips,
                   mfe_pips, mae_pips, mfe_profit, mae_profit
            FROM position_metrics
            WHERE ticket = ?
            """,
            (int(ticket),),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def prune_position_metrics(self, symbol: str, magic: int, open_tickets: set[int]) -> int:
        """Archive and remove telemetry rows for positions no longer open in MT5."""
        cursor = self.connection.execute(
            """
            SELECT ticket, symbol, magic, opened_at, updated_at, side, volume,
                   entry_price, current_price, current_profit, current_pips,
                   mfe_pips, mae_pips, mfe_profit, mae_profit
            FROM position_metrics
            WHERE symbol = ? AND magic = ?
            """,
            (symbol, magic),
        )
        stale_rows = [row for row in cursor.fetchall() if int(row["ticket"]) not in open_tickets]
        stale = [int(row["ticket"]) for row in stale_rows]
        if not stale:
            return 0
        archived_at = _now()
        self.connection.executemany(
            """
            INSERT INTO position_metrics_history (
                archived_at, ticket, symbol, magic, opened_at, updated_at, side, volume,
                entry_price, current_price, current_profit, current_pips,
                mfe_pips, mae_pips, mfe_profit, mae_profit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    archived_at,
                    row["ticket"],
                    row["symbol"],
                    row["magic"],
                    row["opened_at"],
                    row["updated_at"],
                    row["side"],
                    row["volume"],
                    row["entry_price"],
                    row["current_price"],
                    row["current_profit"],
                    row["current_pips"],
                    row["mfe_pips"],
                    row["mae_pips"],
                    row["mfe_profit"],
                    row["mae_profit"],
                )
                for row in stale_rows
            ],
        )
        self.connection.executemany(
            "DELETE FROM position_metrics WHERE ticket = ?",
            [(ticket,) for ticket in stale],
        )
        self.connection.commit()
        return len(stale)

    def get_sent_order_count_since(self, symbol: str, magic: int, since_iso: str) -> int:
        cursor = self.connection.execute(
            """
            SELECT COUNT(*)
            FROM orders
            WHERE phase = 'send'
              AND symbol = ?
              AND json_extract(request_json, '$.magic') = ?
              AND json_extract(request_json, '$.position') IS NULL
              AND created_at >= ?
              AND retcode IN (0, 10008, 10009)
            """,
            (symbol, magic, since_iso),
        )
        return int(cursor.fetchone()[0] or 0)


    def get_pnl_since(self, symbol: str, magic: int, since_iso: str) -> float:
        row = self.connection.execute(
            """
            SELECT COALESCE(SUM(COALESCE(profit, 0) + COALESCE(commission, 0) + COALESCE(swap, 0)), 0.0) pnl
            FROM deals
            WHERE symbol = ? AND magic = ? AND created_at >= ?
            """,
            (symbol, magic, since_iso),
        ).fetchone()
        return float(row["pnl"] if row else 0.0)

    def get_total_pnl_since(self, since_iso: str) -> float:
        row = self.connection.execute(
            """
            SELECT COALESCE(SUM(COALESCE(profit, 0) + COALESCE(commission, 0) + COALESCE(swap, 0)), 0.0) pnl
            FROM deals
            WHERE created_at >= ?
            """,
            (since_iso,),
        ).fetchone()
        return float(row["pnl"] if row else 0.0)

    def get_day_start_equity(self, since_iso: str) -> float | None:
        row = self.connection.execute(
            """
            SELECT equity
            FROM account_snapshots
            WHERE created_at >= ? AND equity IS NOT NULL
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (since_iso,),
        ).fetchone()
        if not row:
            return None
        return float(row["equity"])

    def get_pnl_last_hour(self, symbol: str, magic: int) -> float:
        """Return realized PnL from closed deals for this symbol + magic in the last hour."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        cursor = self.connection.execute(
            """
            SELECT COALESCE(SUM(COALESCE(profit, 0) + COALESCE(commission, 0) + COALESCE(swap, 0)), 0.0)
            FROM deals
            WHERE symbol = ?
              AND magic = ?
              AND entry = 1
              AND created_at >= ?
            """,
            (symbol, magic, cutoff),
        )
        value = cursor.fetchone()[0]
        return float(value or 0.0)

    def get_latest_losing_exit(self, symbol: str, magic: int):
        """Return the latest losing exit deal for this bot, if any.

        Used as a persistent anti-flip guard: unlike in-memory monotonic
        cooldowns, this survives bot restarts and SL/TP broker-side exits.
        """
        cursor = self.connection.execute(
            """
            SELECT created_at, profit, deal_type, price, ticket
            FROM deals
            WHERE symbol = ?
              AND magic = ?
              AND entry = 1
              AND profit < 0
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (symbol, magic),
        )
        return cursor.fetchone()

    def get_consecutive_losses(self, symbol: str, magic: int) -> int:
        """Return the current streak of consecutive losing deals for this bot.

        Looks at the most recent closed deals (exit entries) for the given
        symbol + magic number, counting from the end until a winning deal
        or no more deals.

        Returns:
            int: number of consecutive losses (0 means last trade was a win
                 or no trades recorded yet).
        """
        cursor = self.connection.execute(
            """
            SELECT profit
            FROM deals
            WHERE symbol = ?
              AND magic = ?
              AND entry = 1
            ORDER BY created_at DESC
            LIMIT 20
            """,
            (symbol, magic),
        )
        rows = cursor.fetchall()
        streak = 0
        for row in rows:
            profit = row[0]
            if profit is None:
                continue
            if float(profit) < 0:
                streak += 1
            else:
                break
        return streak


def _pip_size_from_symbol_info(symbol_info) -> float:
    digits = int(getattr(symbol_info, "digits", 5))
    point = float(getattr(symbol_info, "point", 0.00001))
    if digits in {3, 5}:
        return point * 10
    return point


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _time_from_epoch(value) -> str:
    if value is None:
        return _now()
    return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()

