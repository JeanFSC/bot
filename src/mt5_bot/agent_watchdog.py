from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from mt5_bot import notifier
from mt5_bot.agent_runner import load_agent_config
from mt5_bot.config import load_config


@dataclass(frozen=True)
class MT5Health:
    connected: bool
    account_trade_allowed: bool
    account_trade_expert: bool
    terminal_trade_allowed: bool
    tradeapi_disabled: bool
    balance: float
    equity: float
    margin: float
    open_positions: int


@dataclass(frozen=True)
class JournalStatus:
    symbol: str
    last_created_at: datetime | None
    execution_status: str | None
    execution_reason: str | None


@dataclass(frozen=True)
class WatchdogReport:
    created_at: str
    level: str
    reasons: list[str]
    summary: dict[str, Any]
    journals: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _dt_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def evaluate_health(
    *,
    mt5: MT5Health,
    journals: list[JournalStatus],
    now: datetime | None = None,
    floor_equity: float | None = None,
    stale_after_seconds: int = 900,
) -> WatchdogReport:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    critical: list[str] = []
    warnings: list[str] = []

    if not mt5.connected:
        critical.append("mt5_disconnected")
    if not mt5.account_trade_allowed:
        critical.append("account_trade_allowed_false")
    if not mt5.account_trade_expert:
        critical.append("account_trade_expert_false")
    if not mt5.terminal_trade_allowed:
        critical.append("terminal_trade_allowed_false")
    if mt5.tradeapi_disabled:
        critical.append("tradeapi_disabled_true")
    if floor_equity is not None and mt5.equity <= floor_equity:
        critical.append("equity_floor_hit")

    journal_payload: list[dict[str, Any]] = []
    for journal in journals:
        age_seconds = None
        if journal.last_created_at is None:
            warnings.append(f"journal_missing:{journal.symbol}")
        else:
            last = journal.last_created_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            last = last.astimezone(timezone.utc)
            age_seconds = max(0, int((now - last).total_seconds()))
            if age_seconds > stale_after_seconds:
                warnings.append(f"journal_stale:{journal.symbol}")
        journal_payload.append(
            {
                "symbol": journal.symbol,
                "last_created_at": _dt_to_iso(journal.last_created_at),
                "age_seconds": age_seconds,
                "execution_status": journal.execution_status,
                "execution_reason": journal.execution_reason,
            }
        )

    level = "critical" if critical else ("warn" if warnings else "ok")
    reasons = critical + warnings
    return WatchdogReport(
        created_at=now.isoformat(),
        level=level,
        reasons=reasons,
        summary={
            "connected": mt5.connected,
            "account_trade_allowed": mt5.account_trade_allowed,
            "account_trade_expert": mt5.account_trade_expert,
            "terminal_trade_allowed": mt5.terminal_trade_allowed,
            "tradeapi_disabled": mt5.tradeapi_disabled,
            "balance": mt5.balance,
            "equity": mt5.equity,
            "margin": mt5.margin,
            "open_positions": mt5.open_positions,
            "floor_equity": floor_equity,
        },
        journals=journal_payload,
    )


def write_jsonl_report(path: Path | str, report: WatchdogReport) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def load_dotenv(path: Path | str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def collect_mt5_health(env_path: Path | str = ".env") -> MT5Health:
    load_dotenv(env_path)
    import MetaTrader5 as mt5  # imported lazily so unit tests do not require MT5

    login_raw = os.getenv("MT5_LOGIN", "").strip()
    password = os.getenv("MT5_PASSWORD", "").strip()
    server = os.getenv("MT5_SERVER", "").strip()
    terminal_path = os.getenv("MT5_TERMINAL_PATH", "").strip() or None
    login = int(login_raw) if login_raw else None

    initialized = mt5.initialize(path=terminal_path, login=login, password=password, server=server)
    if not initialized:
        return MT5Health(False, False, False, False, False, 0.0, 0.0, 0.0, 0)
    if login is not None:
        mt5.login(login, password=password, server=server)

    account = mt5.account_info()
    terminal = mt5.terminal_info()
    positions = mt5.positions_get() or []
    return MT5Health(
        connected=bool(getattr(terminal, "connected", False)),
        account_trade_allowed=bool(getattr(account, "trade_allowed", False)) if account else False,
        account_trade_expert=bool(getattr(account, "trade_expert", False)) if account else False,
        terminal_trade_allowed=bool(getattr(terminal, "trade_allowed", False)),
        tradeapi_disabled=bool(getattr(terminal, "tradeapi_disabled", False)),
        balance=float(getattr(account, "balance", 0.0) or 0.0) if account else 0.0,
        equity=float(getattr(account, "equity", 0.0) or 0.0) if account else 0.0,
        margin=float(getattr(account, "margin", 0.0) or 0.0) if account else 0.0,
        open_positions=len(positions),
    )


def collect_journal_statuses(agent_config_path: Path | str) -> list[JournalStatus]:
    agent_config = load_agent_config(agent_config_path)
    statuses: list[JournalStatus] = []
    for cfg_path in agent_config.configs:
        bot_cfg = load_config(cfg_path)
        db_path = Path(bot_cfg.database_path)
        if not db_path.exists():
            statuses.append(JournalStatus(bot_cfg.symbol, None, None, "database_missing"))
            continue
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT created_at, execution_status, execution_reason
                FROM trade_journal
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()
            conn.close()
        except Exception as exc:
            statuses.append(JournalStatus(bot_cfg.symbol, None, None, f"journal_error:{exc}"))
            continue
        if row is None:
            statuses.append(JournalStatus(bot_cfg.symbol, None, None, "journal_empty"))
        else:
            statuses.append(
                JournalStatus(
                    bot_cfg.symbol,
                    _parse_iso(row["created_at"]),
                    row["execution_status"],
                    row["execution_reason"],
                )
            )
    return statuses


def _legacy_format_report_corrupt(report: WatchdogReport) -> str:
    summary = report.summary
    reasons = ", ".join(report.reasons) if report.reasons else "none"
    journal_bits = []
    for journal in report.journals:
        age = journal.get("age_seconds")
        age_text = "n/a" if age is None else f"{age}s"
        journal_bits.append(f"{journal['symbol']}:{journal.get('execution_reason')} age={age_text}")
    journals = " | ".join(journal_bits) if journal_bits else "no journals"
    return (
        f"[MT5 Agent Watchdog {report.level.upper()}]\n"
        f"Equity: {summary['equity']:.2f} | Balance: {summary['balance']:.2f} | Positions: {summary['open_positions']}\n"
        f"Trading: acct={summary['account_trade_allowed']} terminal={summary['terminal_trade_allowed']} api_disabled={summary['tradeapi_disabled']}\n"
        f"Reasons: {reasons}\n"
        f"Journals: {journals}"
    )


def format_report(report: WatchdogReport) -> str:
    summary = report.summary
    reasons = ", ".join(report.reasons) if report.reasons else "none"
    journal_bits = []
    for journal in report.journals:
        age = journal.get("age_seconds")
        age_text = "n/a" if age is None else f"{age}s"
        journal_bits.append(f"{journal['symbol']}:{journal.get('execution_reason')} age={age_text}")
    journals = " | ".join(journal_bits) if journal_bits else "no journals"
    return (
        f"[MT5 Agent Watchdog {report.level.upper()}]\n"
        f"Equity: {summary['equity']:.2f} | Balance: {summary['balance']:.2f} | Positions: {summary['open_positions']}\n"
        f"Trading: acct={summary['account_trade_allowed']} terminal={summary['terminal_trade_allowed']} api_disabled={summary['tradeapi_disabled']}\n"
        f"Reasons: {reasons}\n"
        f"Journals: {journals}"
    )


def should_agent_run(report: WatchdogReport) -> bool:
    """Return whether the managed trader process is allowed to run."""
    return report.level != "critical"


def _start_agent(command: list[str]) -> subprocess.Popen:
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return subprocess.Popen(command, cwd=Path.cwd(), env=env)


def _stop_agent(child: subprocess.Popen, reason: str) -> None:
    if child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=20)
    except subprocess.TimeoutExpired:
        notifier.error_alert("WATCHDOG", f"Force killing agent after stop timeout: {reason}")
        child.kill()
        child.wait(timeout=10)


def build_agent_command(agent_config_path: Path | str) -> list[str]:
    return [
        sys.executable,
        "-u",
        "-m",
        "mt5_bot.agent_runner",
        "--agent-config",
        str(agent_config_path),
        "run-continuous",
        "--allow-demo-orders",
    ]


def run_watchdog(
    *,
    agent_config_path: Path | str = "config/autonomous_agent.yaml",
    interval_seconds: int = 900,
    stale_after_seconds: int = 1200,
    report_path: Path | str = "data/watchdog_health.jsonl",
    manage_agent: bool = True,
) -> int:
    agent_config = load_agent_config(agent_config_path)
    child: subprocess.Popen | None = None
    last_level: str | None = None
    command = build_agent_command(agent_config_path)

    try:
        while True:
            mt5_health = collect_mt5_health()
            journals = collect_journal_statuses(agent_config_path)
            report = evaluate_health(
                mt5=mt5_health,
                journals=journals,
                floor_equity=agent_config.floor_equity,
                stale_after_seconds=stale_after_seconds,
            )
            write_jsonl_report(report_path, report)
            message = format_report(report)
            print(message, flush=True)

            if report.level != "ok" or report.level != last_level:
                notifier.notify(message)
            last_level = report.level

            if manage_agent:
                if child is not None and child.poll() is not None:
                    notifier.error_alert("WATCHDOG", f"Agent process exited rc={child.returncode}; restart decision follows health gate")
                    child = None

                if not should_agent_run(report):
                    if child is not None:
                        reason = ", ".join(report.reasons) or "critical_health"
                        notifier.error_alert("WATCHDOG", f"Stopping agent due to critical health: {reason}")
                        _stop_agent(child, reason)
                        child = None
                elif child is None:
                    child = _start_agent(command)
                    notifier.notify("[WATCHDOG] Agent process started")

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        if child is not None and child.poll() is None:
            child.terminate()
        return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_agent_watchdog")
    parser.add_argument("--agent-config", default="config/autonomous_agent.yaml")
    parser.add_argument("--interval-seconds", type=int, default=900)
    parser.add_argument("--stale-after-seconds", type=int, default=1200)
    parser.add_argument("--report-path", default="data/watchdog_health.jsonl")
    parser.add_argument("--no-manage-agent", action="store_true")
    args = parser.parse_args(argv)
    return run_watchdog(
        agent_config_path=args.agent_config,
        interval_seconds=args.interval_seconds,
        stale_after_seconds=args.stale_after_seconds,
        report_path=args.report_path,
        manage_agent=not args.no_manage_agent,
    )


if __name__ == "__main__":
    raise SystemExit(main())
