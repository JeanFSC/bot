from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd


TIMEFRAMES = {
    "M1":  "TIMEFRAME_M1",
    "M5":  "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30",
    "H1":  "TIMEFRAME_H1",
    "H4":  "TIMEFRAME_H4",
}


class MT5Gateway:
    def __init__(self):
        try:
            import MetaTrader5 as mt5
        except ImportError as exc:
            raise RuntimeError("MetaTrader5 package is not installed. Run: pip install -r requirements.txt") from exc
        self.mt5 = mt5

    def initialize(self, terminal_path: str | None = None) -> None:
        ok = self.mt5.initialize(path=terminal_path) if terminal_path else self.mt5.initialize()
        if not ok:
            raise RuntimeError(f"MT5 initialize failed: {self.mt5.last_error()}")

    def login(self, login: int, password: str, server: str) -> None:
        ok = self.mt5.login(login, password=password, server=server)
        if not ok:
            raise RuntimeError(f"MT5 login failed: {self.mt5.last_error()}")

    def shutdown(self) -> None:
        self.mt5.shutdown()

    def account_info(self):
        info = self.mt5.account_info()
        if info is None:
            raise RuntimeError(f"MT5 account_info failed: {self.mt5.last_error()}")
        return info

    def terminal_info(self):
        info = self.mt5.terminal_info()
        if info is None:
            raise RuntimeError(f"MT5 terminal_info failed: {self.mt5.last_error()}")
        return info

    def symbol_info(self, symbol: str):
        info = self.mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"Symbol not found: {symbol}")
        return info

    def symbol_select(self, symbol: str) -> None:
        info = self.symbol_info(symbol)
        if not info.visible and not self.mt5.symbol_select(symbol, True):
            raise RuntimeError(f"MT5 symbol_select failed for {symbol}: {self.mt5.last_error()}")

    def symbol_info_tick(self, symbol: str):
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"MT5 symbol_info_tick failed for {symbol}: {self.mt5.last_error()}")
        return tick

    def copy_rates_from_pos(self, symbol: str, timeframe: str, start_pos: int, count: int) -> pd.DataFrame:
        mt5_timeframe = getattr(self.mt5, TIMEFRAMES[timeframe])
        rates = self.mt5.copy_rates_from_pos(symbol, mt5_timeframe, start_pos, count)
        if rates is None:
            raise RuntimeError(f"MT5 copy_rates_from_pos failed: {self.mt5.last_error()}")
        frame = pd.DataFrame(rates)
        frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
        return frame

    def copy_rates_range(self, symbol: str, timeframe: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
        mt5_timeframe = getattr(self.mt5, TIMEFRAMES[timeframe])
        rates = self.mt5.copy_rates_range(symbol, mt5_timeframe, date_from, date_to)
        if rates is None:
            raise RuntimeError(f"MT5 copy_rates_range failed: {self.mt5.last_error()}")
        frame = pd.DataFrame(rates)
        frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
        return frame

    def copy_ticks_from(self, symbol: str, from_time: datetime, count: int, flags: int | None = None) -> pd.DataFrame:
        flags = self.mt5.COPY_TICKS_ALL if flags is None else flags
        ticks = self.mt5.copy_ticks_from(symbol, from_time, count, flags)
        if ticks is None:
            raise RuntimeError(f"MT5 copy_ticks_from failed: {self.mt5.last_error()}")
        frame = pd.DataFrame(ticks)
        if not frame.empty and "time" in frame:
            frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
        return frame

    def positions_get(self, symbol: str | None = None):
        positions = self.mt5.positions_get(symbol=symbol) if symbol else self.mt5.positions_get()
        if positions is None:
            raise RuntimeError(f"MT5 positions_get failed: {self.mt5.last_error()}")
        return list(positions)

    def order_check(self, request: dict[str, Any]):
        result = self.mt5.order_check(request)
        if result is None:
            raise RuntimeError(f"MT5 order_check failed: {self.mt5.last_error()}")
        return result

    def order_send(self, request: dict[str, Any]):
        result = self.mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"MT5 order_send failed: {self.mt5.last_error()}")
        return result

    def order_modify(self, ticket: int, sl: float, tp: float) -> Any:
        """Modify SL/TP of an open position (TRADE_ACTION_SLTP).

        Used by the trailing-stop engine to lock in profits without closing.
        Returns the order_send result.
        """
        request = {
            "action": self.mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": sl,
            "tp": tp,
        }
        result = self.mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"MT5 order_modify failed: {self.mt5.last_error()}")
        return result

    def history_deals_get(self, date_from: datetime, date_to: datetime, group: str | None = None):
        deals = self.mt5.history_deals_get(date_from, date_to, group=group) if group else self.mt5.history_deals_get(date_from, date_to)
        if deals is None:
            raise RuntimeError(f"MT5 history_deals_get failed: {self.mt5.last_error()}")
        return list(deals)

    def constants(self) -> dict[str, int]:
        names = [
            "TRADE_ACTION_DEAL",
            "TRADE_ACTION_SLTP",
            "ORDER_TYPE_BUY",
            "ORDER_TYPE_SELL",
            "ORDER_TIME_GTC",
            "ORDER_FILLING_FOK",
            "ORDER_FILLING_IOC",
            "ORDER_FILLING_RETURN",
        ]
        return {name: getattr(self.mt5, name) for name in names if hasattr(self.mt5, name)}
