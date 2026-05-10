#!/usr/bin/env python3
"""Validate backtest PnL formula against broker specs.

For each symbol, compute the expected USD profit/loss for a hypothetical
1-lot trade with a 100-pip move, using:
  (a) the backtest's hardcoded _PIP_VALUE_PER_LOT, and
  (b) broker specs from data/diag/symbol_specs.json (if available)

If the JSON is missing, falls back to documented broker defaults
(IC Markets / OANDA / typical retail) so the script is useful in sandbox too.

Usage:
    python scripts/diag_pnl_validator.py

This script does NOT require MetaTrader5. It only does math.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Documented broker defaults (typical retail, IC Markets / OANDA scale)
# Used as fallback when symbol_specs.json is not available.
_TYPICAL_BROKER_SPECS = {
    "EURUSD": {"contract_size": 100_000, "tick_size": 0.00001, "tick_value": 1.0},
    "GBPUSD": {"contract_size": 100_000, "tick_size": 0.00001, "tick_value": 1.0},
    "AUDUSD": {"contract_size": 100_000, "tick_size": 0.00001, "tick_value": 1.0},
    "NZDUSD": {"contract_size": 100_000, "tick_size": 0.00001, "tick_value": 1.0},
    "USDCAD": {"contract_size": 100_000, "tick_size": 0.00001, "tick_value": 0.76},
    "USDCHF": {"contract_size": 100_000, "tick_size": 0.00001, "tick_value": 1.10},
    "USDJPY": {"contract_size": 100_000, "tick_size": 0.001,   "tick_value": 0.91},
    "GBPJPY": {"contract_size": 100_000, "tick_size": 0.001,   "tick_value": 0.91},
    "XAUUSD": {"contract_size": 100,     "tick_size": 0.01,    "tick_value": 1.0},   # 1 oz x $0.01 x 100 = $1
    "XAGUSD": {"contract_size": 5_000,   "tick_size": 0.001,   "tick_value": 5.0},   # 5000 oz x $0.001 = $5
}


def _pip_size(symbol: str) -> float:
    """Mirror of strategy._pip_size_for_symbol."""
    s = symbol.upper().replace("/", "")
    if s.startswith(("XAU", "XAG", "GOLD", "SILVER")):
        return 0.01
    if "JPY" in s:
        return 0.01
    return 0.0001


def _broker_pip_value(symbol: str, specs: dict) -> float:
    """Compute pip value per lot from broker tick specs."""
    pip = _pip_size(symbol)
    return specs["tick_value"] * (pip / specs["tick_size"])


def _broker_pnl_from_pips(symbol: str, lot: float, pips: float, specs: dict) -> float:
    """Compute USD P&L from a pip move using broker specs."""
    pip_val = _broker_pip_value(symbol, specs)
    return pips * lot * pip_val


def main() -> int:
    from mt5_bot.backtest_engine import _PIP_VALUE_PER_LOT

    # Try to load real broker specs from MT5 diag run (if exists)
    diag_path = Path("data/diag/symbol_specs.json")
    real_specs: dict[str, dict] = {}
    if diag_path.exists():
        for row in json.loads(diag_path.read_text()):
            sym = row["symbol"]
            real_specs[sym] = {
                "contract_size": row["trade_contract_size"],
                "tick_size":     row["trade_tick_size"],
                "tick_value":    row["trade_tick_value"],
            }
        print(f"Loaded broker specs from {diag_path}")
        source = "broker (MT5)"
    else:
        real_specs = _TYPICAL_BROKER_SPECS
        print("No data/diag/symbol_specs.json found - using typical retail defaults")
        print("(Run scripts/diag_symbol_specs.py on Windows for real broker numbers)")
        source = "typical retail"

    print(f"\nValidation: 1 lot x 100 pips move, using {source} specs vs backtest formula\n")
    print(f"{'Symbol':<10} {'pip_v_broker':>13} {'pip_v_bt':>10} {'PnL_broker':>12} "
          f"{'PnL_bt':>10} {'Delta%':>8} {'verdict'}")
    print("-" * 90)

    bugs: list[dict] = []
    for symbol in _PIP_VALUE_PER_LOT.keys():
        if symbol not in real_specs:
            continue
        specs = real_specs[symbol]

        pip_v_broker = _broker_pip_value(symbol, specs)
        pip_v_bt     = _PIP_VALUE_PER_LOT[symbol]
        pnl_broker   = _broker_pnl_from_pips(symbol, 1.0, 100.0, specs)
        pnl_bt       = 100.0 * 1.0 * pip_v_bt

        if pip_v_broker > 0:
            delta_pct = (pnl_bt - pnl_broker) / pnl_broker * 100
        else:
            delta_pct = 0.0

        if abs(delta_pct) > 5:
            verdict = f"FAIL {abs(delta_pct):.0f}% off"
            bugs.append({
                "symbol": symbol,
                "pip_v_broker": pip_v_broker,
                "pip_v_bt": pip_v_bt,
                "delta_pct": delta_pct,
                "suggested_fix": round(pip_v_broker, 4),
            })
        else:
            verdict = "OK"

        print(f"{symbol:<10} {pip_v_broker:>13.4f} {pip_v_bt:>10.2f} "
              f"${pnl_broker:>10.2f} ${pnl_bt:>8.2f} {delta_pct:>+7.1f}% {verdict}")

    print(f"\n{'-'*60}")
    if bugs:
        print(f"BUGS FOUND ({len(bugs)}):")
        for b in bugs:
            direction = "INFLATES" if b["delta_pct"] > 0 else "UNDERSTATES"
            print(f"  - {b['symbol']}: hardcoded={b['pip_v_bt']:.2f} -> "
                  f"should be {b['suggested_fix']:.4f}  ({direction} P&L by {abs(b['delta_pct']):.0f}%)")
        print("\nFix: update _PIP_VALUE_PER_LOT in src/mt5_bot/backtest_engine.py")
        return 1
    else:
        print("All pip_values consistent with broker specs (within 5%).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
