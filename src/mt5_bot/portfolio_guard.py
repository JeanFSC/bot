from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class PortfolioGuardDecision:
    allow_new_entry: bool
    reason: str
    margin_pct: float
    open_positions: int


@dataclass(frozen=True)
class PortfolioOverlapScore:
    """Signal-level overlap/de-scoring decision.

    PortfolioGuardDecision is the hard account gate used before expensive signal
    work. This object is softer and richer: once a bot has a real BUY/SELL
    signal, it scores whether that new entry is just duplicated exposure.
    """

    allow_new_entry: bool
    reason: str
    risk_multiplier: float = 1.0
    score_penalty: float = 0.0
    exact_symbol_positions: int = 0
    same_currency_positions: int = 0
    same_direction_theme_positions: int = 0
    overlap_reasons: tuple[str, ...] = field(default_factory=tuple)


def symbol_currencies(symbol: str) -> set[str]:
    """Best-effort FX/metal currency buckets for correlation/exposure checks."""
    symbol = symbol.upper().replace("/", "")
    if symbol.startswith("XAU") or symbol.startswith("GOLD"):
        return {"XAU", "USD"}
    if symbol.startswith("XAG") or symbol.startswith("SILVER"):
        return {"XAG", "USD"}
    if len(symbol) >= 6:
        return {symbol[:3], symbol[3:6]}
    return {symbol}


def signal_direction_value(signal_type) -> int | None:
    """Normalize BUY/SELL signal values to MT5 position type values.

    MT5 positions use 0=BUY and 1=SELL. Accepts SignalType enum, strings, or
    None to keep portfolio_guard.py independent from strategy.py.
    """
    value = getattr(signal_type, "value", signal_type)
    value = str(value).upper() if value is not None else ""
    if value == "BUY":
        return 0
    if value == "SELL":
        return 1
    return None


def position_direction_value(position) -> int | None:
    try:
        return int(getattr(position, "type"))
    except Exception:
        return None


def _positions_list(positions: Iterable | None) -> list:
    return list(positions or [])


def portfolio_guard_decision(config, account, positions) -> PortfolioGuardDecision:
    """Block only *new* entries when account exposure is already excessive.

    This is intentionally not a profit cap: existing winners keep running and
    trailing/TP logic can continue. The guard prevents stacking too many fresh
    positions on top of already-used margin or one crowded currency theme.
    """
    positions = _positions_list(positions)
    equity = float(getattr(account, "equity", 0) or 0)
    margin = float(getattr(account, "margin", 0) or 0)
    margin_pct = (margin / equity * 100.0) if equity > 0 else 0.0

    max_margin = float(getattr(config, "max_total_margin_pct", 85.0))
    if margin_pct >= max_margin:
        return PortfolioGuardDecision(False, f"portfolio_margin_{margin_pct:.1f}_pct", margin_pct, len(positions))

    max_positions = int(getattr(config, "max_portfolio_open_positions", 3))
    if len(positions) >= max_positions:
        return PortfolioGuardDecision(False, f"portfolio_positions_{len(positions)}", margin_pct, len(positions))

    max_same_ccy = int(getattr(config, "max_same_currency_positions", 2))
    current_ccy = symbol_currencies(getattr(config, "symbol", ""))
    same_theme = 0
    for pos in positions:
        if symbol_currencies(str(getattr(pos, "symbol", ""))) & current_ccy:
            same_theme += 1
    if same_theme >= max_same_ccy:
        return PortfolioGuardDecision(False, f"same_currency_exposure_{same_theme}", margin_pct, len(positions))

    return PortfolioGuardDecision(True, "ok", margin_pct, len(positions))


def score_portfolio_overlap(config, positions, signal_type) -> PortfolioOverlapScore:
    """De-score a real signal for direct/correlated portfolio overlap.

    Hard blocks:
    - exact same symbol already open at/above max_exact_symbol_positions
    - same-currency/theme exposure at/above max_same_currency_positions

    Soft penalties:
    - any same-currency exposure reduces risk
    - same-direction theme crowding reduces risk more

    This prevents the 12-bot suite from pretending to be diversified when many
    bots are actually the same USD/JPY/gold theme.
    """
    positions = _positions_list(positions)
    current_symbol = str(getattr(config, "symbol", "")).upper().replace("/", "")
    current_ccy = symbol_currencies(current_symbol)
    signal_dir = signal_direction_value(signal_type)

    exact = 0
    same_ccy = 0
    same_dir_theme = 0
    reasons: list[str] = []

    for pos in positions:
        pos_symbol = str(getattr(pos, "symbol", "")).upper().replace("/", "")
        if not pos_symbol:
            continue
        pos_ccy = symbol_currencies(pos_symbol)
        overlaps_theme = bool(pos_ccy & current_ccy)
        if pos_symbol == current_symbol:
            exact += 1
            reasons.append(f"exact_symbol:{pos_symbol}")
        if overlaps_theme:
            same_ccy += 1
            pos_dir = position_direction_value(pos)
            if signal_dir is not None and pos_dir == signal_dir:
                same_dir_theme += 1
                reasons.append(f"same_direction_theme:{pos_symbol}")

    max_exact = int(getattr(config, "max_exact_symbol_positions", 1))
    if exact >= max_exact:
        return PortfolioOverlapScore(
            False,
            f"exact_symbol_overlap_{exact}",
            risk_multiplier=0.0,
            score_penalty=5.0,
            exact_symbol_positions=exact,
            same_currency_positions=same_ccy,
            same_direction_theme_positions=same_dir_theme,
            overlap_reasons=tuple(reasons),
        )

    max_same_ccy = int(getattr(config, "max_same_currency_positions", 2))
    if same_ccy >= max_same_ccy:
        return PortfolioOverlapScore(
            False,
            f"same_currency_overlap_{same_ccy}",
            risk_multiplier=0.0,
            score_penalty=4.0,
            exact_symbol_positions=exact,
            same_currency_positions=same_ccy,
            same_direction_theme_positions=same_dir_theme,
            overlap_reasons=tuple(reasons),
        )

    max_same_dir_theme = int(getattr(config, "max_same_direction_theme_positions", 1))
    if max_same_dir_theme > 0 and same_dir_theme >= max_same_dir_theme:
        return PortfolioOverlapScore(
            False,
            f"same_direction_theme_overlap_{same_dir_theme}",
            risk_multiplier=0.0,
            score_penalty=4.5,
            exact_symbol_positions=exact,
            same_currency_positions=same_ccy,
            same_direction_theme_positions=same_dir_theme,
            overlap_reasons=tuple(reasons),
        )

    risk_multiplier = 1.0
    score_penalty = 0.0
    if same_dir_theme >= 1:
        risk_multiplier *= 0.50
        score_penalty += 2.0
        reasons.append("risk_halved_same_direction_theme")
    elif same_ccy >= 1:
        risk_multiplier *= 0.75
        score_penalty += 1.0
        reasons.append("risk_reduced_same_currency_theme")

    return PortfolioOverlapScore(
        True,
        "ok" if not reasons else "soft_overlap_descore",
        risk_multiplier=risk_multiplier,
        score_penalty=score_penalty,
        exact_symbol_positions=exact,
        same_currency_positions=same_ccy,
        same_direction_theme_positions=same_dir_theme,
        overlap_reasons=tuple(reasons),
    )
