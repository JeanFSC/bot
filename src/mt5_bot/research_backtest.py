from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from mt5_bot.research_strategy import ResearchSetup, detect_research_signal
from mt5_bot.strategy import SignalType, _pip_size_for_symbol


@dataclass(frozen=True)
class ResearchTrade:
    entry_time: str
    exit_time: str
    symbol: str
    side: str
    setup: str
    quality: str
    entry: float
    exit: float
    pnl_pips: float
    r_multiple: float
    reason: str
    exit_reason: str
    market_state: str
    session: str


@dataclass(frozen=True)
class ResearchBacktestResult:
    symbol: str
    trades: int
    wins: int
    losses: int
    net_pips: float
    expectancy_pips: float
    profit_factor: float | None
    avg_win: float
    avg_loss: float
    trades_detail: list[ResearchTrade]


def _exit_trade(
    future: pd.DataFrame,
    side: SignalType,
    sl: float,
    tp: float,
    max_bars: int,
) -> tuple[int, float, str]:
    for offset, (_, row) in enumerate(future.iloc[:max_bars].iterrows(), start=1):
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])
        if side is SignalType.BUY:
            if low <= sl:
                return offset, sl, "sl"
            if high >= tp:
                return offset, tp, "tp"
        elif side is SignalType.SELL:
            if high >= sl:
                return offset, sl, "sl"
            if low <= tp:
                return offset, tp, "tp"
        if offset == max_bars:
            return offset, close, "time_stop"
    if future.empty:
        return 0, 0.0, "no_future"
    row = future.iloc[-1]
    return len(future), float(row["close"]), "end_of_data"


def run_research_backtest(
    rates: pd.DataFrame,
    symbol: str,
    lookback: int = 48,
    max_hold_bars: int = 24,
    session_name: str = "all",
    session_start_hour: int | None = None,
    session_end_hour: int | None = None,
) -> ResearchBacktestResult:
    pip = _pip_size_for_symbol(symbol)
    trades: list[ResearchTrade] = []
    i = max(lookback + 30, 80)
    while i < len(rates) - 2:
        if session_start_hour is not None and session_end_hour is not None:
            ts = pd.Timestamp(rates.iloc[i]["time"])
            hour = int(ts.hour)
            if session_start_hour <= session_end_hour:
                in_session = session_start_hour <= hour < session_end_hour
            else:
                in_session = hour >= session_start_hour or hour < session_end_hour
            if not in_session:
                i += 1
                continue

        window = rates.iloc[: i + 1].copy()
        signal = detect_research_signal(window, symbol=symbol, lookback=lookback)
        if signal.type is SignalType.NONE or signal.entry is None or signal.sl is None or signal.tp is None:
            i += 1
            continue

        future = rates.iloc[i + 1: i + 1 + max_hold_bars]
        bars_held, exit_price, exit_reason = _exit_trade(future, signal.type, signal.sl, signal.tp, max_hold_bars)
        if bars_held <= 0:
            break

        entry = float(signal.entry)
        raw = exit_price - entry
        pnl_pips = raw / pip if signal.type is SignalType.BUY else -raw / pip
        risk = abs(entry - float(signal.sl))
        r_multiple = (abs(exit_price - entry) / risk if risk else 0.0)
        if pnl_pips < 0:
            r_multiple = -r_multiple

        entry_time = str(rates.iloc[i]["time"])
        exit_time = str(rates.iloc[min(i + bars_held, len(rates) - 1)]["time"])
        trades.append(ResearchTrade(
            entry_time=entry_time,
            exit_time=exit_time,
            symbol=symbol,
            side=signal.type.value,
            setup=(signal.setup.value if isinstance(signal.setup, ResearchSetup) else str(signal.setup)),
            quality=signal.quality,
            entry=round(entry, 6),
            exit=round(exit_price, 6),
            pnl_pips=round(pnl_pips, 2),
            r_multiple=round(r_multiple, 2),
            reason=signal.reason,
            exit_reason=exit_reason,
            market_state=signal.market_state,
            session=session_name,
        ))
        i += max(1, bars_held)

    wins = [t.pnl_pips for t in trades if t.pnl_pips > 0]
    losses = [t.pnl_pips for t in trades if t.pnl_pips <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    total = sum(t.pnl_pips for t in trades)
    count = len(trades)
    return ResearchBacktestResult(
        symbol=symbol,
        trades=count,
        wins=len(wins),
        losses=len(losses),
        net_pips=round(total, 2),
        expectancy_pips=round(total / count, 2) if count else 0.0,
        profit_factor=(round(gross_win / gross_loss, 2) if gross_loss else None),
        avg_win=round(gross_win / len(wins), 2) if wins else 0.0,
        avg_loss=round(sum(losses) / len(losses), 2) if losses else 0.0,
        trades_detail=trades,
    )
