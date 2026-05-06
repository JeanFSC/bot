from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EquityStopDecision:
    stop: bool
    reason: str | None


def equity_stop_decision(equity: float, target_equity: float | None = None, floor_equity: float | None = None) -> EquityStopDecision:
    if floor_equity is not None and equity <= floor_equity:
        return EquityStopDecision(True, "floor_equity_hit")
    if target_equity is not None and equity >= target_equity:
        return EquityStopDecision(True, "target_equity_hit")
    return EquityStopDecision(False, None)
