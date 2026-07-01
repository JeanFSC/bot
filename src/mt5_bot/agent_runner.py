from __future__ import annotations

import argparse
import datetime
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Sequence

import yaml

from mt5_bot.autonomous_agent import EvolutionMemory
from mt5_bot.cli import run_check
from mt5_bot.config import load_config
from mt5_bot.postmortem import sync_postmortems


class AgentMode(str, Enum):
    PREFLIGHT = "preflight"
    PAPER = "paper"
    DEMO = "demo"


@dataclass(frozen=True)
class AgentRunnerConfig:
    configs: list[Path]
    memory_db: Path = Path("data/agent_memory.sqlite")
    mode: AgentMode = AgentMode.PAPER
    max_parallel_bots: int = 1
    max_seconds: int = 0
    poll_seconds: int | None = None
    prioritize_live_positions: bool = True
    allow_demo_orders: bool = False
    reduced_risk_pct: float = 0.10
    target_equity: float | None = None
    floor_equity: float | None = None


def load_agent_config(path: str | Path) -> AgentRunnerConfig:
    cfg_path = Path(path)
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Agent config must be a YAML object")
    configs = [Path(item) for item in raw.get("configs", [])]
    if not configs:
        raise ValueError("Agent config requires at least one config path")
    mode = AgentMode(str(raw.get("mode", "paper")).lower())
    return AgentRunnerConfig(
        configs=configs,
        memory_db=Path(raw.get("memory_db", "data/agent_memory.sqlite")),
        mode=mode,
        max_parallel_bots=int(raw.get("max_parallel_bots", 1)),
        max_seconds=int(raw.get("max_seconds", 0)),
        poll_seconds=int(raw["poll_seconds"]) if raw.get("poll_seconds") is not None else None,
        prioritize_live_positions=bool(raw.get("prioritize_live_positions", True)),
        allow_demo_orders=bool(raw.get("allow_demo_orders", False)),
        reduced_risk_pct=float(raw.get("reduced_risk_pct", 0.10)),
        target_equity=float(raw["target_equity"]) if raw.get("target_equity") is not None else None,
        floor_equity=float(raw["floor_equity"]) if raw.get("floor_equity") is not None else None,
    )


def preflight(config: AgentRunnerConfig) -> int:
    memory = EvolutionMemory(config.memory_db)
    memory.close()
    for cfg in config.configs:
        loaded = load_config(cfg)
        if not loaded.account or not loaded.account.demo_only:
            print(f"BLOCKED {cfg}: account.demo_only must be true")
            return 2
        if loaded.execution.trade_enabled:
            print(f"BLOCKED {cfg}: YAML trade_enabled must remain false; use mode=demo + allow flag")
            return 2
        print(f"CHECK {cfg} symbol={loaded.symbol} tf={loaded.timeframe} magic={loaded.execution.magic}")
        rc = run_check(str(cfg))
        if rc != 0:
            print(f"FAILED {cfg}: MT5 check rc={rc}")
            return rc
    print(f"AGENT_PREFLIGHT_OK configs={len(config.configs)} memory={config.memory_db}")
    return 0


def learn_from_closed_deals(config: AgentRunnerConfig) -> int:
    memory = EvolutionMemory(config.memory_db)
    learned = 0
    postmortems = 0
    try:
        for cfg_path in config.configs:
            bot_cfg = load_config(cfg_path)
            db_path = bot_cfg.database_path
            if not db_path.exists():
                continue
            postmortems += sync_postmortems(db_path)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT ticket, created_at, symbol, profit, commission, swap, magic, deal_type, comment
                    FROM deals
                    WHERE entry = 1 AND symbol = ? AND magic = ?
                    ORDER BY created_at ASC
                    """,
                    (bot_cfg.symbol, bot_cfg.execution.magic),
                ).fetchall()
                for row in rows:
                    pnl = float(row["profit"] or 0.0) + float(row["commission"] or 0.0) + float(row["swap"] or 0.0)
                    hour = 12
                    try:
                        hour = int(str(row["created_at"])[11:13])
                    except Exception:
                        pass
                    side = "BUY" if int(row["deal_type"] or 0) == 1 else "SELL"
                    setup_key = f"{row['symbol']}:{side}:closed_deal:trend_unknown:{_session_bucket(hour)}"
                    before = memory.get_setup_stats(row["symbol"], setup_key)
                    after = memory.record_outcome(
                        symbol=row["symbol"],
                        setup_key=setup_key,
                        pnl=pnl,
                        reason="closed_deal_import",
                        context={
                            "ticket": row["ticket"],
                            "magic": row["magic"],
                            "comment": row["comment"],
                            "source_db": str(db_path),
                        },
                        source_id=f"{db_path}:{row['ticket']}",
                    )
                    if after != before:
                        learned += 1
            finally:
                conn.close()
    finally:
        memory.close()
    print(f"AGENT_LEARN_OK learned={learned} postmortems={postmortems} memory={config.memory_db}")
    return learned


def _run_single_config(config: AgentRunnerConfig, cfg: Path) -> int:
    cmd = [
        sys.executable,
        "-m",
        "mt5_bot",
        "trade",
        "--config",
        str(cfg),
    ]
    if config.max_seconds > 0:
        cmd.extend(["--max-seconds", str(config.max_seconds)])
    if config.poll_seconds is not None:
        cmd.extend(["--poll-seconds", str(config.poll_seconds)])
    if config.target_equity is not None:
        cmd.extend(["--target-equity", str(config.target_equity)])
    if config.floor_equity is not None:
        cmd.extend(["--floor-equity", str(config.floor_equity)])
    if config.mode is AgentMode.DEMO:
        cmd.append("--trade-enabled")
    cmd.append("--db")
    cmd.append(str(load_config(str(cfg)).database_path))
    print("RUN", " ".join(cmd))
    env = dict(os.environ)
    env["MT5_AGENT_MEMORY_DB"] = str(config.memory_db)
    completed = subprocess.run(cmd, check=False, env=env)
    if completed.returncode == 0:
        # Learn from trades after each successful run
        learn_from_closed_deals(config)
    return completed.returncode


def _active_position_keys() -> set[tuple[str, int]]:
    """Return currently open MT5 positions as (symbol, magic) keys."""
    try:
        from mt5_bot.mt5_gateway import MT5Gateway

        gateway = MT5Gateway()
        try:
            gateway.initialize()
            positions = gateway.positions_get() or []
            return {
                (str(getattr(position, "symbol")), int(getattr(position, "magic")))
                for position in positions
            }
        finally:
            gateway.shutdown()
    except Exception as exc:
        print(f"WARN: live position priority unavailable: {exc}")
        return set()


def _configs_prioritizing_live_positions(config: AgentRunnerConfig) -> list[Path]:
    if not config.prioritize_live_positions:
        return list(config.configs)

    active = _active_position_keys()
    if not active:
        return list(config.configs)

    indexed = list(enumerate(config.configs))

    def sort_key(item: tuple[int, Path]) -> tuple[int, int]:
        index, cfg_path = item
        try:
            loaded = load_config(cfg_path)
            is_live = (loaded.symbol, int(loaded.execution.magic)) in active
        except Exception:
            is_live = False
        return (0 if is_live else 1, index)

    ordered = [cfg_path for _, cfg_path in sorted(indexed, key=sort_key)]
    if ordered != list(config.configs):
        print(f"LIVE_POSITION_PRIORITY active={len(active)} order={[str(path) for path in ordered]}")
    return ordered


def run_once(config: AgentRunnerConfig) -> int:
    if config.mode is AgentMode.DEMO and not config.allow_demo_orders:
        print("BLOCKED: mode=demo requires allow_demo_orders=true")
        return 2
    if config.max_parallel_bots != 1:
        print("BLOCKED: MVP runner currently supports max_parallel_bots=1 for controlled verification")
        return 2
    learn_from_closed_deals(config)
    for cfg in config.configs:
        return _run_single_config(config, cfg)
    return 0


def run_continuous(config: AgentRunnerConfig) -> int:
    """Run the agent continuously, cycling through configs forever.

    Restarts each config when it finishes (by max-seconds, floor-equity, or user stop),
    and learns from closed deals after each cycle. This is the learning loop.
    """
    if config.mode is AgentMode.DEMO and not config.allow_demo_orders:
        print("BLOCKED: mode=demo requires allow_demo_orders=true")
        return 2
    if config.max_parallel_bots != 1:
        print("BLOCKED: MVP runner currently supports max_parallel_bots=1 for controlled verification")
        return 2

    print(f"AGENT_CONTINUOUS_START mode={config.mode.value} floor={config.floor_equity} risk_pct={config.reduced_risk_pct}")

    iteration = 0
    while True:
        iteration += 1
        print(f"\n### CONTINUOUS CYCLE #{iteration} ### {datetime.datetime.now(datetime.timezone.utc)} ###")

        for cfg in _configs_prioritizing_live_positions(config):
            print(f"Processing {cfg}...")
            rc = _run_single_config(config, cfg)
            if rc != 0:
                print(f"WARN: {cfg} exited with rc={rc}, restarting after short sleep...")
                time.sleep(5)
                # Continue to next symbol; the loop restarts it on next cycle
                continue
            sleep_between = max(2, config.poll_seconds or 15) if config.poll_seconds else 15
            print(f"Sleeping {sleep_between}s before next symbol...")
            time.sleep(sleep_between)

        # After completing all configs, learn globally
        print(f"\n### LEARNING PHASE ###")
        learn_from_closed_deals(config)

        print(f"### END CYCLE #{iteration} ###")
        time.sleep(1)


def _session_bucket(hour_utc: int) -> str:
    if 7 <= hour_utc < 12:
        return "session_london"
    if 12 <= hour_utc < 17:
        return "session_london_ny"
    if 17 <= hour_utc < 22:
        return "session_ny"
    return "session_asia"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_autonomous_agent")
    parser.add_argument("--agent-config", default="config/autonomous_agent.yaml")
    parser.add_argument("command", choices=["preflight", "learn", "run-once", "run-continuous"])
    parser.add_argument("--allow-demo-orders", action="store_true")
    parser.add_argument("--max-seconds", type=int, default=None)
    args = parser.parse_args(argv)

    config = load_agent_config(args.agent_config)
    if args.max_seconds is not None:
        config = AgentRunnerConfig(**{**config.__dict__, "max_seconds": args.max_seconds})
    if args.allow_demo_orders:
        config = AgentRunnerConfig(**{**config.__dict__, "allow_demo_orders": True})

    if args.command == "preflight":
        return preflight(config)
    if args.command == "learn":
        learn_from_closed_deals(config)
        return 0
    if args.command == "run-once":
        return run_once(config)
    if args.command == "run-continuous":
        return run_continuous(config)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
