from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from mt5_bot.agent_runner import load_agent_config
from mt5_bot.cli import _connect_and_validate, setup_logging
from mt5_bot.config import BotConfig, load_config
from mt5_bot.executor import ExecutionResult, TradeExecutor
from mt5_bot.mt5_gateway import MT5Gateway
from mt5_bot.risk import spread_pips
from mt5_bot.storage import BotStorage
from mt5_bot.strategy import StrategyConfig, detect_signal, detect_signal_mtf


@dataclass(frozen=True)
class SupervisorAction:
    symbol: str
    magic: int
    status: str
    reason: str


@dataclass(frozen=True)
class ActionPolicy:
    can_manage_risk: bool
    can_add_risk: bool
    reason: str


@dataclass(frozen=True)
class SupervisorReport:
    checked_positions: int
    managed_positions: int
    unknown_positions: int
    action_mode: str
    action_policy: str
    actions: list[SupervisorAction]


def run_once(
    agent_config_path: str | Path = "config/autonomous_agent.yaml",
    *,
    allow_trade_actions: bool = False,
    heat_report_path: str | Path = "data/portfolio_heat.jsonl",
    heat_max_age_seconds: int = 60,
    gateway: MT5Gateway | None = None,
) -> SupervisorReport:
    """Manage all open positions owned by the active autonomous configs.

    This supervisor never searches for new entries. It only applies the
    deterministic live-position controls already used by the trade loop:
    telemetry, early exit, time stop, winner scaling, profit lock, partial
    close, and trailing stop.
    """
    agent_config = load_agent_config(agent_config_path)
    config_by_key = _load_config_map(agent_config.configs, allow_trade_actions=allow_trade_actions)
    if not config_by_key:
        return SupervisorReport(0, 0, 0, _action_mode(allow_trade_actions), "no_configs", [])

    own_gateway = gateway is None
    gateway = gateway or MT5Gateway()
    first_config = next(iter(config_by_key.values()))
    actions: list[SupervisorAction] = []
    checked_positions = 0
    managed_keys: set[tuple[str, int]] = set()
    unknown_positions = 0
    action_policy = _action_policy(
        allow_trade_actions=allow_trade_actions,
        heat_report_path=heat_report_path,
        max_age_seconds=heat_max_age_seconds,
    )

    try:
        if own_gateway:
            _connect_and_validate(gateway, first_config)

        positions = gateway.positions_get() or []
        for position in positions:
            checked_positions += 1
            key = (str(getattr(position, "symbol", "")), int(getattr(position, "magic", 0) or 0))
            config = config_by_key.get(key)
            if config is None:
                unknown_positions += 1
                continue
            if key in managed_keys:
                continue
            managed_keys.add(key)
            actions.extend(_manage_config_positions(gateway, config, action_policy=action_policy))
    finally:
        if own_gateway:
            gateway.shutdown()

    return SupervisorReport(
        checked_positions=checked_positions,
        managed_positions=len(managed_keys),
        unknown_positions=unknown_positions,
        action_mode=_action_mode(allow_trade_actions),
        action_policy=action_policy.reason,
        actions=actions,
    )


def run_continuous(
    agent_config_path: str | Path = "config/autonomous_agent.yaml",
    *,
    allow_trade_actions: bool = False,
    interval_seconds: int = 5,
    report_path: str | Path = "data/live_position_supervisor.jsonl",
    heat_report_path: str | Path = "data/portfolio_heat.jsonl",
    heat_max_age_seconds: int = 60,
) -> int:
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    while True:
        report = run_once(
            agent_config_path,
            allow_trade_actions=allow_trade_actions,
            heat_report_path=heat_report_path,
            heat_max_age_seconds=heat_max_age_seconds,
        )
        _append_report(report_file, report)
        time.sleep(max(1, interval_seconds))


def _load_config_map(config_paths: Sequence[Path], *, allow_trade_actions: bool) -> dict[tuple[str, int], BotConfig]:
    result: dict[tuple[str, int], BotConfig] = {}
    for path in config_paths:
        config = load_config(path)
        if allow_trade_actions:
            config = replace(config, execution=replace(config.execution, trade_enabled=True))
        key = (config.symbol, int(config.execution.magic))
        if key in result:
            raise ValueError(f"Duplicate live-position owner config for symbol/magic: {key[0]} {key[1]}")
        result[key] = config
    return result


def _manage_config_positions(
    gateway: MT5Gateway,
    config: BotConfig,
    *,
    action_policy: ActionPolicy | None = None,
) -> list[SupervisorAction]:
    storage = BotStorage(config.database_path)
    executor = TradeExecutor(gateway, storage, config)
    actions: list[SupervisorAction] = []
    action_policy = action_policy or ActionPolicy(False, False, "report_only")
    try:
        _record_missing_sl_tp(gateway, storage, config, actions)
        actions.extend(_wrap_results(config, executor.record_position_metrics()))
        if not config.execution.trade_enabled:
            return actions
        if not action_policy.can_manage_risk:
            reason = f"supervisor_actions_blocked_{action_policy.reason}"
            storage.record_runtime_event(
                "live_position_supervisor",
                reason,
                symbol=config.symbol,
                magic=config.execution.magic,
                level="warning",
                context={"policy": action_policy.reason},
            )
            actions.append(SupervisorAction(config.symbol, int(config.execution.magic), "blocked", reason))
            return actions

        current_spread = _current_spread(gateway, config)
        signal = _management_signal(gateway, config)
        if signal.atr_pips and signal.atr_pips > 0:
            actions.extend(_wrap_results(config, executor.manage_no_favorable_excursion(signal.atr_pips)))
        actions.extend(_wrap_results(config, executor.manage_time_stops()))
        if signal.atr_pips and signal.atr_pips > 0:
            if action_policy.can_add_risk:
                actions.extend(_wrap_results(config, executor.manage_winner_scaling(signal.atr_pips, signal.adx, current_spread)))
            elif bool(getattr(config, "winner_scaling_enabled", False)):
                reason = f"winner_scale_blocked_{action_policy.reason}"
                storage.record_runtime_event(
                    "live_position_supervisor",
                    reason,
                    symbol=config.symbol,
                    magic=config.execution.magic,
                    level="warning",
                    context={"policy": action_policy.reason},
                )
                actions.append(SupervisorAction(config.symbol, int(config.execution.magic), "blocked", reason))
            actions.extend(_wrap_results(config, executor.manage_profit_lock(signal.atr_pips)))
            actions.extend(_wrap_results(config, executor.manage_partial_close(signal.atr_pips)))
            if config.strategy.use_trailing_stop:
                actions.extend(_wrap_results(config, executor.manage_trailing_stops(signal.atr_pips)))
    finally:
        storage.close()
    return actions


def _action_policy(
    *,
    allow_trade_actions: bool,
    heat_report_path: str | Path,
    max_age_seconds: int,
) -> ActionPolicy:
    if not allow_trade_actions:
        return ActionPolicy(False, False, "report_only")
    heat = _read_latest_jsonl(heat_report_path)
    if heat is None:
        return ActionPolicy(False, False, "portfolio_heat_missing")
    age = _report_age_seconds(heat)
    if age is None or age > max_age_seconds:
        return ActionPolicy(False, False, "portfolio_heat_stale")
    if int(heat.get("unknown_positions", 0) or 0) > 0:
        return ActionPolicy(False, False, "unknown_positions")
    if int(heat.get("unprotected_positions", 0) or 0) > 0:
        return ActionPolicy(True, False, "unprotected_positions")
    decision = str(heat.get("decision") or "")
    if decision == "block_new_entries_recommended":
        return ActionPolicy(True, False, "portfolio_heat_blocks_add_risk")
    if decision == "reduce_or_wait_recommended":
        return ActionPolicy(True, False, "portfolio_heat_reduce_or_wait")
    if decision == "allow_new_entries":
        return ActionPolicy(True, True, "portfolio_heat_allows_actions")
    return ActionPolicy(False, False, "portfolio_heat_unknown_decision")


def _read_latest_jsonl(path: str | Path) -> dict | None:
    file_path = Path(path)
    if not file_path.exists():
        return None
    latest = ""
    with file_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if raw.strip():
                latest = raw.strip()
    if not latest:
        return None
    try:
        payload = json.loads(latest)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _report_age_seconds(payload: dict) -> float | None:
    created_at = payload.get("created_at")
    if not created_at:
        return None
    try:
        created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - created.astimezone(timezone.utc)).total_seconds())


def _action_mode(allow_trade_actions: bool) -> str:
    return "demo_actions_enabled" if allow_trade_actions else "report_only"


def _management_signal(gateway: MT5Gateway, config: BotConfig):
    strategy_config = StrategyConfig(**{
        field: getattr(config.strategy, field)
        for field in StrategyConfig.__dataclass_fields__  # type: ignore[attr-defined]
    })
    signal_rates = gateway.copy_rates_from_pos(config.symbol, config.timeframe, 0, 300)
    use_mtf = config.strategy.use_trend_filter and config.trend_timeframe != config.timeframe
    if use_mtf:
        trend_bars = max(config.strategy.trend_ema * 3, 200)
        trend_rates = gateway.copy_rates_from_pos(config.symbol, config.trend_timeframe, 0, trend_bars)
        return detect_signal_mtf(signal_rates, trend_rates, strategy_config, symbol=config.symbol)
    return detect_signal(signal_rates, strategy_config, symbol=config.symbol)


def _current_spread(gateway: MT5Gateway, config: BotConfig) -> float:
    tick = gateway.symbol_info_tick(config.symbol)
    symbol_info = gateway.symbol_info(config.symbol)
    return spread_pips(float(tick.bid), float(tick.ask), symbol_info)


def _record_missing_sl_tp(
    gateway: MT5Gateway,
    storage: BotStorage,
    config: BotConfig,
    actions: list[SupervisorAction],
) -> None:
    positions = gateway.positions_get(symbol=config.symbol) or []
    for position in positions:
        if int(getattr(position, "magic", 0) or 0) != int(config.execution.magic):
            continue
        has_sl = float(getattr(position, "sl", 0.0) or 0.0) > 0
        has_tp = float(getattr(position, "tp", 0.0) or 0.0) > 0
        if has_sl and has_tp:
            continue
        reason = "missing_sl_tp"
        storage.record_runtime_event(
            "live_position_supervisor",
            reason,
            symbol=config.symbol,
            magic=config.execution.magic,
            level="critical",
            context={
                "ticket": int(getattr(position, "ticket", 0) or 0),
                "has_sl": has_sl,
                "has_tp": has_tp,
            },
        )
        actions.append(SupervisorAction(config.symbol, int(config.execution.magic), "alert", reason))


def _wrap_results(config: BotConfig, results: list[ExecutionResult]) -> list[SupervisorAction]:
    return [
        SupervisorAction(
            symbol=config.symbol,
            magic=int(config.execution.magic),
            status=result.status,
            reason=result.reason,
        )
        for result in results
    ]


def _append_report(path: Path, report: SupervisorReport) -> None:
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checked_positions": report.checked_positions,
        "managed_positions": report.managed_positions,
        "unknown_positions": report.unknown_positions,
        "action_mode": report.action_mode,
        "action_policy": report.action_policy,
        "actions": [action.__dict__ for action in report.actions],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_live_position_supervisor")
    parser.add_argument("command", choices=["run-once", "run-continuous"])
    parser.add_argument("--agent-config", default="config/autonomous_agent.yaml")
    parser.add_argument("--allow-demo-actions", action="store_true")
    parser.add_argument("--interval-seconds", type=int, default=5)
    parser.add_argument("--report-path", default="data/live_position_supervisor.jsonl")
    parser.add_argument("--heat-report-path", default="data/portfolio_heat.jsonl")
    parser.add_argument("--heat-max-age-seconds", type=int, default=60)
    args = parser.parse_args(argv)

    setup_logging(log_name="live_position_supervisor")
    if args.command == "run-once":
        report = run_once(
            args.agent_config,
            allow_trade_actions=args.allow_demo_actions,
            heat_report_path=args.heat_report_path,
            heat_max_age_seconds=args.heat_max_age_seconds,
        )
        print(json.dumps({
            "checked_positions": report.checked_positions,
            "managed_positions": report.managed_positions,
            "unknown_positions": report.unknown_positions,
            "action_mode": report.action_mode,
            "action_policy": report.action_policy,
            "actions": [action.__dict__ for action in report.actions],
        }, indent=2, sort_keys=True))
        return 0
    if args.command == "run-continuous":
        return run_continuous(
            args.agent_config,
            allow_trade_actions=args.allow_demo_actions,
            interval_seconds=args.interval_seconds,
            report_path=args.report_path,
            heat_report_path=args.heat_report_path,
            heat_max_age_seconds=args.heat_max_age_seconds,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
