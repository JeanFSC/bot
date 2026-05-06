from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from mt5_bot.config import BotConfig
from mt5_bot.strategy import SignalType, StrategyConfig, detect_signal, _pip_size_for_symbol


@dataclass(frozen=True)
class BacktestResult:
    trades: int
    wins: int
    losses: int
    net_pips: float


def run_backtest(rates: pd.DataFrame, config: BotConfig) -> BacktestResult:
    strategy_config = StrategyConfig(**config.strategy.__dict__)
    pip_size = _pip_size_for_symbol(config.symbol)
    trades = 0
    wins = 0
    losses = 0
    net_pips = 0.0
    position: tuple[SignalType, float] | None = None

    for end in range(max(config.strategy.slow_ema + 5, 30), len(rates)):
        window = rates.iloc[: end + 1].copy()
        signal = detect_signal(window, strategy_config)
        if signal.type is SignalType.NONE or signal.price is None:
            continue

        if position is not None and position[0] is signal.type:
            continue

        if position is not None:
            direction, entry = position
            delta = signal.price - entry
            pips = delta / pip_size if direction is SignalType.BUY else -delta / pip_size
            net_pips += pips
            wins += int(pips > 0)
            losses += int(pips <= 0)
            trades += 1

        position = (signal.type, signal.price)

    return BacktestResult(trades=trades, wins=wins, losses=losses, net_pips=round(net_pips, 2))
