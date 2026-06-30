from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from mt5_bot.strategy import Signal, SignalType


class AgentDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REDUCE_RISK = "REDUCE_RISK"
    SKIP = "SKIP"


@dataclass(frozen=True)
class SetupStats:
    symbol: str
    setup_key: str
    wins: int = 0
    losses: int = 0
    net_pnl: float = 0.0
    consecutive_losses: int = 0
    risk_multiplier: float = 1.0

    @property
    def trades(self) -> int:
        return self.wins + self.losses

    @property
    def winrate(self) -> float:
        return self.wins / self.trades if self.trades else 0.0


class EvolutionMemory:
    """Persistent trading memory for setup-level learning.

    This is intentionally simple and auditable. It does not invent signals; it
    records outcomes by setup key, adjusts a risk multiplier, and can block
    repeated losing contexts. The goal is evolutionary risk control, not curve
    fitting.
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_setup_stats (
                symbol TEXT NOT NULL,
                setup_key TEXT NOT NULL,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                net_pnl REAL NOT NULL DEFAULT 0.0,
                consecutive_losses INTEGER NOT NULL DEFAULT 0,
                risk_multiplier REAL NOT NULL DEFAULT 1.0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (symbol, setup_key)
            );

            CREATE TABLE IF NOT EXISTS agent_lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT UNIQUE,
                created_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                setup_key TEXT NOT NULL,
                outcome TEXT NOT NULL,
                pnl REAL NOT NULL,
                reason TEXT NOT NULL,
                risk_multiplier_after REAL NOT NULL,
                context_json TEXT NOT NULL
            );
            """
        )
        existing = {row[1] for row in self.connection.execute("PRAGMA table_info(agent_lessons)")}
        if "source_id" not in existing:
            self.connection.execute("ALTER TABLE agent_lessons ADD COLUMN source_id TEXT")
            self.connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_lessons_source_id ON agent_lessons(source_id)")
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def get_setup_stats(self, symbol: str, setup_key: str) -> SetupStats:
        row = self.connection.execute(
            """
            SELECT symbol, setup_key, wins, losses, net_pnl, consecutive_losses, risk_multiplier
            FROM agent_setup_stats
            WHERE symbol = ? AND setup_key = ?
            """,
            (symbol, setup_key),
        ).fetchone()
        if not row:
            return SetupStats(symbol=symbol, setup_key=setup_key)
        return SetupStats(
            symbol=row["symbol"],
            setup_key=row["setup_key"],
            wins=int(row["wins"]),
            losses=int(row["losses"]),
            net_pnl=float(row["net_pnl"]),
            consecutive_losses=int(row["consecutive_losses"]),
            risk_multiplier=float(row["risk_multiplier"]),
        )

    def record_outcome(
        self,
        symbol: str,
        setup_key: str,
        pnl: float,
        reason: str,
        context: dict[str, Any] | None = None,
        source_id: str | None = None,
    ) -> SetupStats:
        before = self.get_setup_stats(symbol, setup_key)
        if source_id is not None:
            existing = self.connection.execute(
                "SELECT id FROM agent_lessons WHERE source_id = ?",
                (source_id,),
            ).fetchone()
            if existing:
                return before
        is_win = float(pnl) > 0
        wins = before.wins + (1 if is_win else 0)
        losses = before.losses + (0 if is_win else 1)
        net_pnl = before.net_pnl + float(pnl)
        consecutive_losses = 0 if is_win else before.consecutive_losses + 1
        risk_multiplier = _next_risk_multiplier(before.risk_multiplier, is_win, consecutive_losses, net_pnl)
        now = _now()

        self.connection.execute(
            """
            INSERT INTO agent_setup_stats (
                symbol, setup_key, wins, losses, net_pnl, consecutive_losses, risk_multiplier, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, setup_key) DO UPDATE SET
                wins=excluded.wins,
                losses=excluded.losses,
                net_pnl=excluded.net_pnl,
                consecutive_losses=excluded.consecutive_losses,
                risk_multiplier=excluded.risk_multiplier,
                updated_at=excluded.updated_at
            """,
            (symbol, setup_key, wins, losses, net_pnl, consecutive_losses, risk_multiplier, now),
        )
        self.connection.execute(
            """
            INSERT INTO agent_lessons (
                source_id, created_at, symbol, setup_key, outcome, pnl, reason, risk_multiplier_after, context_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                now,
                symbol,
                setup_key,
                "win" if is_win else "loss",
                float(pnl),
                reason,
                risk_multiplier,
                json.dumps(context or {}, default=str),
            ),
        )
        self.connection.commit()
        return self.get_setup_stats(symbol, setup_key)


def classify_setup(symbol: str, signal: Signal, hour_utc: int) -> str:
    trend = f"trend_{signal.trend_bias or 'unknown'}"
    session = _session_bucket(hour_utc)
    return f"{symbol}:{signal.type.value}:{signal.reason}:{trend}:{session}"


def decide_trade(
    symbol: str,
    signal: Signal,
    memory: EvolutionMemory,
    hour_utc: int,
    spread_pips: float,
    max_spread_pips: float,
    min_confidence: float,
    max_consecutive_setup_losses: int,
) -> AgentDecision:
    if signal.type is SignalType.NONE:
        return AgentDecision.SKIP
    if spread_pips > max_spread_pips:
        return AgentDecision.BLOCK

    setup_key = classify_setup(symbol, signal, hour_utc)
    stats = memory.get_setup_stats(symbol, setup_key)
    if stats.consecutive_losses >= max_consecutive_setup_losses:
        return AgentDecision.BLOCK

    confidence = signal_confidence(signal, spread_pips=spread_pips, max_spread_pips=max_spread_pips)
    if confidence < min_confidence:
        return AgentDecision.BLOCK
    if stats.risk_multiplier < 0.95:
        return AgentDecision.REDUCE_RISK
    return AgentDecision.ALLOW


def adjusted_risk_pct(
    memory: EvolutionMemory,
    symbol: str,
    setup_key: str,
    base_risk_pct: float,
    floor_pct: float = 0.05,
) -> float:
    stats = memory.get_setup_stats(symbol, setup_key)
    return max(float(floor_pct), float(base_risk_pct) * stats.risk_multiplier)


def signal_confidence(signal: Signal, spread_pips: float, max_spread_pips: float) -> float:
    if signal.type is SignalType.NONE:
        return 0.0
    score = 0.50
    if signal.trend_bias:
        if signal.type is SignalType.BUY and signal.trend_bias == "up":
            score += 0.15
        elif signal.type is SignalType.SELL and signal.trend_bias == "down":
            score += 0.15
    if signal.adx is not None and signal.adx >= 24:
        score += 0.10
    if signal.rsi is not None:
        if signal.type is SignalType.BUY and 40 <= signal.rsi <= 65:
            score += 0.10
        if signal.type is SignalType.SELL and 35 <= signal.rsi <= 60:
            score += 0.10
    if signal.atr_pips is not None and signal.atr_pips > 0:
        score += 0.05
    if max_spread_pips > 0:
        score -= min(0.20, max(0.0, spread_pips / max_spread_pips) * 0.15)
    return max(0.0, min(1.0, score))


def _next_risk_multiplier(previous: float, is_win: bool, consecutive_losses: int, net_pnl: float) -> float:
    if is_win:
        # Recover slowly after proof of improvement, never above baseline.
        return min(1.0, previous + 0.05)
    penalty = 0.20 if consecutive_losses >= 2 else 0.15
    if net_pnl < 0:
        penalty += 0.05
    return max(0.20, previous - penalty)


def _session_bucket(hour_utc: int) -> str:
    if 7 <= hour_utc < 12:
        return "session_london"
    if 12 <= hour_utc < 17:
        return "session_london_ny"
    if 17 <= hour_utc < 22:
        return "session_ny"
    return "session_asia"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
