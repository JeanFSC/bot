from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from mt5_bot.config import RiskConfig
from mt5_bot.strategy import SignalType


@dataclass(frozen=True)
class OrderPrices:
    sl: float
    tp: float


@dataclass(frozen=True)
class DailyRiskState:
    day: date
    start_equity: float
    current_equity: float
    trades_count: int


def pip_size(symbol_info) -> float:
    if int(symbol_info.digits) in {3, 5}:
        return float(symbol_info.point) * 10
    return float(symbol_info.point)


def spread_pips(bid: float, ask: float, symbol_info) -> float:
    return (ask - bid) / pip_size(symbol_info)


def normalize_volume(volume: float, symbol_info) -> float:
    step = float(symbol_info.volume_step)
    minimum = float(symbol_info.volume_min)
    maximum = float(symbol_info.volume_max)
    normalized = math.floor(volume / step) * step
    normalized = max(minimum, min(maximum, normalized))
    decimals = max(0, len(str(step).split(".")[-1].rstrip("0")))
    return round(normalized, decimals)


def calculate_volume(config: RiskConfig, equity: float, symbol_info) -> float:
    if config.mode == "fixed_lot":
        return normalize_volume(config.fixed_lot, symbol_info)

    pip_value_per_lot = _pip_value_per_lot(symbol_info)
    risk_amount = equity * (config.risk_pct / 100)
    raw_volume = risk_amount / (config.sl_pips * pip_value_per_lot)
    return normalize_volume(raw_volume, symbol_info)


def _pip_value_per_lot(symbol_info) -> float:
    tick_value = float(symbol_info.trade_tick_value or 0)
    tick_size = float(symbol_info.trade_tick_size or 0)
    if tick_value <= 0 or tick_size <= 0:
        raise ValueError("Symbol tick value and tick size are required for percent_equity risk")
    return tick_value * (pip_size(symbol_info) / tick_size)


def prices_for_order(signal_type: SignalType, entry_price: float, sl_pips: float, tp_pips: float, symbol_info) -> OrderPrices:
    pip = pip_size(symbol_info)
    if signal_type is SignalType.BUY:
        sl = entry_price - sl_pips * pip
        tp = entry_price + tp_pips * pip
    elif signal_type is SignalType.SELL:
        sl = entry_price + sl_pips * pip
        tp = entry_price - tp_pips * pip
    else:
        raise ValueError("Cannot calculate prices for NONE signal")
    digits = int(symbol_info.digits)
    return OrderPrices(sl=round(sl, digits), tp=round(tp, digits))


def is_daily_loss_limit_hit(state: DailyRiskState, max_daily_loss_pct: float) -> bool:
    loss_pct = ((state.start_equity - state.current_equity) / state.start_equity) * 100
    return loss_pct >= max_daily_loss_pct


def is_trade_count_limit_hit(state: DailyRiskState, max_trades_per_day: int) -> bool:
    return state.trades_count >= max_trades_per_day
