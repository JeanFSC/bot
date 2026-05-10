from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioGuardDecision:
    allow_new_entry: bool
    reason: str
    margin_pct: float
    open_positions: int


def symbol_currencies(symbol: str) -> set[str]:
    """Best-effort FX/metal currency buckets for correlation/exposure checks."""
    symbol = symbol.upper()
    if symbol.startswith("XAU"):
        return {"XAU", "USD"}
    if len(symbol) >= 6:
        return {symbol[:3], symbol[3:6]}
    return {symbol}


def portfolio_guard_decision(config, account, positions) -> PortfolioGuardDecision:
    """Block only *new* entries when account exposure is already excessive.

    This is intentionally not a profit cap: existing winners keep running and
    trailing/TP logic can continue. The guard prevents stacking too many fresh
    positions on top of already-used margin or one crowded currency theme.
    """
    positions = list(positions or [])
    equity = float(getattr(account, "equity", 0) or 0)
    margin = float(getattr(account, "margin", 0) or 0)
    margin_pct = (margin / equity * 100.0) if equity > 0 else 0.0

    # Same-symbol guard: only one bot may hold a position on a given symbol
    own_symbol = str(getattr(config, "symbol", ""))
    _execution = getattr(config, "execution", None)
    own_magic = int(getattr(_execution, "magic", 0)) if _execution else 0
    other_sym_pos = [
        p for p in positions
        if str(getattr(p, "symbol", "")) == own_symbol and int(getattr(p, "magic", 0)) != own_magic
    ]
    if other_sym_pos:
        other_magic = int(getattr(other_sym_pos[0], "magic", 0))
        return PortfolioGuardDecision(False, f"same_symbol_active_magic_{other_magic}", margin_pct, len(positions))

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
