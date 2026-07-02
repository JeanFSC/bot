from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from mt5_bot.agent_runner import load_agent_config
from mt5_bot.cli import _connect_and_validate, setup_logging
from mt5_bot.config import BotConfig, load_config
from mt5_bot.mt5_gateway import MT5Gateway
from mt5_bot.portfolio_guard import symbol_currencies


@dataclass(frozen=True)
class PositionHeat:
    ticket: int
    symbol: str
    magic: int
    side: str
    volume: float
    profit: float
    sl: float
    tp: float
    risk_to_sl_usd: float | None
    reward_to_tp_usd: float | None
    has_sl: bool
    has_tp: bool


@dataclass(frozen=True)
class PortfolioHeatReport:
    checked_positions: int
    owned_positions: int
    unknown_positions: int
    equity: float
    margin: float
    margin_pct: float
    floating_pnl: float
    risk_to_sl_usd: float
    risk_to_sl_pct: float
    reward_to_tp_usd: float
    unprotected_positions: int
    decision: str
    reasons: list[str]
    currency_exposure: dict[str, int]
    symbol_exposure: dict[str, int]
    positions: list[PositionHeat]


def run_once(
    agent_config_path: str | Path = "config/autonomous_agent.yaml",
    *,
    gateway: MT5Gateway | None = None,
) -> PortfolioHeatReport:
    agent_config = load_agent_config(agent_config_path)
    configs = [load_config(path) for path in agent_config.configs]
    config_by_key = build_config_map(configs)

    own_gateway = gateway is None
    gateway = gateway or MT5Gateway()
    first_config = configs[0] if configs else None
    try:
        if own_gateway and first_config is not None:
            _connect_and_validate(gateway, first_config)
        account = gateway.account_info()
        positions = gateway.positions_get() or []
        return build_heat_report(gateway, account, positions, config_by_key)
    finally:
        if own_gateway:
            gateway.shutdown()


def build_config_map(configs: Sequence[BotConfig]) -> dict[tuple[str, int], BotConfig]:
    result: dict[tuple[str, int], BotConfig] = {}
    for config in configs:
        key = (config.symbol, int(config.execution.magic))
        if key in result:
            raise ValueError(f"Duplicate portfolio owner config for symbol/magic: {key[0]} {key[1]}")
        result[key] = config
    return result


def build_heat_report(
    gateway,
    account,
    positions: Sequence,
    config_by_key: dict[tuple[str, int], BotConfig],
) -> PortfolioHeatReport:
    equity = float(getattr(account, "equity", 0.0) or 0.0)
    margin = float(getattr(account, "margin", 0.0) or 0.0)
    margin_pct = (margin / equity * 100.0) if equity > 0 else 0.0
    floating_pnl = sum(float(getattr(position, "profit", 0.0) or 0.0) for position in positions)

    heat_positions: list[PositionHeat] = []
    unknown_positions = 0
    currency_exposure: dict[str, int] = {}
    symbol_exposure: dict[str, int] = {}

    for position in positions:
        symbol = str(getattr(position, "symbol", ""))
        magic = int(getattr(position, "magic", 0) or 0)
        key = (symbol, magic)
        if key not in config_by_key:
            unknown_positions += 1
            continue

        heat = _position_heat(gateway, position)
        heat_positions.append(heat)
        symbol_exposure[symbol] = symbol_exposure.get(symbol, 0) + 1
        for currency in symbol_currencies(symbol):
            currency_exposure[currency] = currency_exposure.get(currency, 0) + 1

    risk_to_sl_usd = sum(item.risk_to_sl_usd or 0.0 for item in heat_positions)
    reward_to_tp_usd = sum(item.reward_to_tp_usd or 0.0 for item in heat_positions)
    risk_to_sl_pct = (risk_to_sl_usd / equity * 100.0) if equity > 0 else 0.0
    unprotected = sum(1 for item in heat_positions if not item.has_sl)

    decision, reasons = _decision(
        config_by_key.values(),
        margin_pct=margin_pct,
        risk_to_sl_pct=risk_to_sl_pct,
        unprotected_positions=unprotected,
        owned_positions=len(heat_positions),
        currency_exposure=currency_exposure,
    )

    return PortfolioHeatReport(
        checked_positions=len(positions),
        owned_positions=len(heat_positions),
        unknown_positions=unknown_positions,
        equity=equity,
        margin=margin,
        margin_pct=margin_pct,
        floating_pnl=floating_pnl,
        risk_to_sl_usd=risk_to_sl_usd,
        risk_to_sl_pct=risk_to_sl_pct,
        reward_to_tp_usd=reward_to_tp_usd,
        unprotected_positions=unprotected,
        decision=decision,
        reasons=reasons,
        currency_exposure=dict(sorted(currency_exposure.items())),
        symbol_exposure=dict(sorted(symbol_exposure.items())),
        positions=heat_positions,
    )


def run_continuous(
    agent_config_path: str | Path = "config/autonomous_agent.yaml",
    *,
    interval_seconds: int = 15,
    report_path: str | Path = "data/portfolio_heat.jsonl",
) -> int:
    report_file = Path(report_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    while True:
        report = run_once(agent_config_path)
        _append_report(report_file, report)
        time.sleep(max(5, interval_seconds))


def _position_heat(gateway, position) -> PositionHeat:
    ticket = int(getattr(position, "ticket", 0) or 0)
    symbol = str(getattr(position, "symbol", ""))
    magic = int(getattr(position, "magic", 0) or 0)
    pos_type = int(getattr(position, "type", 0) or 0)
    side = "BUY" if pos_type == 0 else "SELL"
    volume = float(getattr(position, "volume", 0.0) or 0.0)
    entry = float(getattr(position, "price_open", 0.0) or 0.0)
    sl = float(getattr(position, "sl", 0.0) or 0.0)
    tp = float(getattr(position, "tp", 0.0) or 0.0)
    profit = float(getattr(position, "profit", 0.0) or 0.0)
    has_sl = sl > 0
    has_tp = tp > 0

    risk_to_sl = None
    if has_sl:
        projected_sl = float(gateway.order_calc_profit(pos_type, symbol, volume, entry, sl))
        risk_to_sl = max(0.0, -projected_sl)

    reward_to_tp = None
    if has_tp:
        projected_tp = float(gateway.order_calc_profit(pos_type, symbol, volume, entry, tp))
        reward_to_tp = max(0.0, projected_tp)

    return PositionHeat(
        ticket=ticket,
        symbol=symbol,
        magic=magic,
        side=side,
        volume=volume,
        profit=profit,
        sl=sl,
        tp=tp,
        risk_to_sl_usd=risk_to_sl,
        reward_to_tp_usd=reward_to_tp,
        has_sl=has_sl,
        has_tp=has_tp,
    )


def _decision(
    configs: Sequence[BotConfig],
    *,
    margin_pct: float,
    risk_to_sl_pct: float,
    unprotected_positions: int,
    owned_positions: int,
    currency_exposure: dict[str, int],
) -> tuple[str, list[str]]:
    configs = list(configs)
    max_margin = min((float(config.max_total_margin_pct) for config in configs), default=35.0)
    max_positions = max((int(config.max_portfolio_open_positions) for config in configs), default=10)
    max_same_currency = max((int(config.max_same_currency_positions) for config in configs), default=6)
    max_loss_pct = min((float(config.max_daily_loss_pct) for config in configs), default=2.0)

    reasons: list[str] = []
    if unprotected_positions:
        reasons.append(f"unprotected_positions_{unprotected_positions}")
    if margin_pct >= max_margin:
        reasons.append(f"margin_{margin_pct:.1f}_pct_gte_{max_margin:.1f}")
    if owned_positions >= max_positions:
        reasons.append(f"positions_{owned_positions}_gte_{max_positions}")
    if risk_to_sl_pct >= max_loss_pct:
        reasons.append(f"risk_to_sl_{risk_to_sl_pct:.2f}_pct_gte_{max_loss_pct:.2f}")

    crowded = [
        f"{currency}:{count}"
        for currency, count in sorted(currency_exposure.items())
        if count >= max_same_currency
    ]
    if crowded:
        reasons.append("crowded_currency_" + ",".join(crowded))

    if unprotected_positions or risk_to_sl_pct >= max_loss_pct or margin_pct >= max_margin:
        return "block_new_entries_recommended", reasons
    if reasons:
        return "reduce_or_wait_recommended", reasons
    return "allow_new_entries", ["ok"]


def _report_payload(report: PortfolioHeatReport) -> dict:
    return {
        "checked_positions": report.checked_positions,
        "owned_positions": report.owned_positions,
        "unknown_positions": report.unknown_positions,
        "equity": report.equity,
        "margin": report.margin,
        "margin_pct": report.margin_pct,
        "floating_pnl": report.floating_pnl,
        "risk_to_sl_usd": report.risk_to_sl_usd,
        "risk_to_sl_pct": report.risk_to_sl_pct,
        "reward_to_tp_usd": report.reward_to_tp_usd,
        "unprotected_positions": report.unprotected_positions,
        "decision": report.decision,
        "reasons": report.reasons,
        "currency_exposure": report.currency_exposure,
        "symbol_exposure": report.symbol_exposure,
        "positions": [position.__dict__ for position in report.positions],
    }


def _append_report(path: Path, report: PortfolioHeatReport) -> None:
    payload = {"created_at": datetime.now(timezone.utc).isoformat(), **_report_payload(report)}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mt5_portfolio_heat")
    parser.add_argument("command", choices=["run-once", "run-continuous"])
    parser.add_argument("--agent-config", default="config/autonomous_agent.yaml")
    parser.add_argument("--interval-seconds", type=int, default=15)
    parser.add_argument("--report-path", default="data/portfolio_heat.jsonl")
    args = parser.parse_args(argv)

    setup_logging(log_name="portfolio_heat")
    if args.command == "run-once":
        report = run_once(args.agent_config)
        print(json.dumps(_report_payload(report), indent=2, sort_keys=True))
        return 0
    if args.command == "run-continuous":
        return run_continuous(
            args.agent_config,
            interval_seconds=args.interval_seconds,
            report_path=args.report_path,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
