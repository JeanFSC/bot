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
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
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
            """
        )
        self.connection.commit()

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

    def record_order_result(self, request: dict[str, Any], send_result) -> None:
        self._record_order(request, send_result, "send")

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

    def _record_order(self, request: dict[str, Any], result, phase: str) -> None:
        result_payload = result._asdict() if hasattr(result, "_asdict") else {"result": str(result)}
        self.connection.execute(
            """
            INSERT INTO orders (
                created_at, symbol, action, order_type, volume, price, sl, tp,
                retcode, comment, phase, request_json, result_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        self.connection.commit()

    def get_avg_spread_last_hour(self, symbol: str) -> float:
        """Return the average spread (pips) for this symbol over the last hour."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        cursor = self.connection.execute(
            "SELECT AVG(spread_pips) FROM market_metrics WHERE symbol = ? AND created_at >= ?",
            (symbol, cutoff),
        )
        row = cursor.fetchone()
        return float(row[0]) if row and row[0] else 0.0

    def get_pnl_last_hour(self, symbol: str, magic: int) -> float:
        """Return realized PnL from closed deals for this symbol + magic in the last hour."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        cursor = self.connection.execute(
            """
            SELECT COALESCE(SUM(profit), 0.0)
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _time_from_epoch(value) -> str:
    if value is None:
        return _now()
    return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
