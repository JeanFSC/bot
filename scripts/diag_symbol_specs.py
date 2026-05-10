#!/usr/bin/env python3
"""Print MT5 symbol specs and validate backtest pip_value against broker data.

Run on Windows with MT5 installed:

    python scripts/diag_symbol_specs.py

Output:
  - Console: aligned table with broker specs vs backtest hardcoded values
  - data/diag/symbol_specs.json: machine-readable for next steps
  - Flags any pip_value mismatch > 5%

This script does NOT trade. It only reads symbol metadata.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Symbols to diagnose (the ones that drive 90% of bot activity)
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "GBPJPY", "AUDUSD", "NZDUSD",
           "USDCAD", "USDCHF", "XAUUSD", "XAGUSD"]


def _expected_pip_size(symbol: str) -> float:
    """Mirror of strategy._pip_size_for_symbol - what the backtest assumes."""
    s = symbol.upper().replace("/", "")
    if s.startswith(("XAU", "XAG", "GOLD", "SILVER")):
        return 0.01
    if "JPY" in s:
        return 0.01
    return 0.0001


def main() -> int:
    try:
        import MetaTrader5 as mt5  # type: ignore[import]
    except ImportError:
        print("ERROR: MetaTrader5 module not installed.", file=sys.stderr)
        print("Install with: pip install MetaTrader5", file=sys.stderr)
        return 1

    if not mt5.initialize():
        print(f"ERROR: mt5.initialize() failed: {mt5.last_error()}", file=sys.stderr)
        return 1

    from mt5_bot.backtest_engine import _PIP_VALUE_PER_LOT

    out_dir = Path("data/diag")
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    print(f"\n{'Symbol':<10} {'digits':>6} {'point':>10} {'tick_sz':>10} {'tick_v':>10} "
          f"{'contract':>10} {'pip_sz':>8} {'pip_v_calc':>11} {'pip_v_bt':>9} {'mismatch':>10}")
    print("-" * 110)

    for symbol in SYMBOLS:
        info = mt5.symbol_info(symbol)
        if info is None:
            print(f"{symbol:<10} NOT AVAILABLE in this terminal - skipping")
            continue

        # Try to enable in Market Watch if not already
        if not info.visible:
            mt5.symbol_select(symbol, True)
            info = mt5.symbol_info(symbol)

        digits        = int(info.digits)
        point         = float(info.point)
        tick_size     = float(info.trade_tick_size or 0)
        tick_value    = float(info.trade_tick_value or 0)
        contract_size = float(info.trade_contract_size or 0)
        spread        = int(info.spread)
        stops_level   = int(info.trade_stops_level)
        vol_min       = float(info.volume_min)
        vol_max       = float(info.volume_max)
        vol_step      = float(info.volume_step)
        currency_base = info.currency_base
        currency_prof = info.currency_profit

        pip_size_assumed = _expected_pip_size(symbol)

        # Pip value computed from broker spec:
        #   pip_value_per_lot = tick_value * (pip_size / tick_size)
        if tick_size > 0:
            pip_v_broker = tick_value * (pip_size_assumed / tick_size)
        else:
            pip_v_broker = float("nan")

        pip_v_backtest = _PIP_VALUE_PER_LOT.get(symbol, 10.0)

        mismatch_pct = (
            abs(pip_v_broker - pip_v_backtest) / pip_v_broker * 100
            if pip_v_broker > 0 else float("nan")
        )

        flag = ""
        if pip_v_broker > 0 and mismatch_pct > 5:
            flag = " BUG"

        print(f"{symbol:<10} {digits:>6} {point:>10.5f} {tick_size:>10.5f} "
              f"{tick_value:>10.4f} {contract_size:>10.0f} {pip_size_assumed:>8.4f} "
              f"{pip_v_broker:>11.4f} {pip_v_backtest:>9.2f} {mismatch_pct:>9.1f}%{flag}")

        rows.append({
            "symbol": symbol,
            "digits": digits,
            "point": point,
            "trade_tick_size": tick_size,
            "trade_tick_value": tick_value,
            "trade_contract_size": contract_size,
            "spread_points": spread,
            "spread_pips_estimate": round(spread * point / pip_size_assumed, 2),
            "trade_stops_level": stops_level,
            "volume_min": vol_min,
            "volume_max": vol_max,
            "volume_step": vol_step,
            "currency_base": currency_base,
            "currency_profit": currency_prof,
            "pip_size_backtest_assumes": pip_size_assumed,
            "pip_value_per_lot_broker_calc": round(pip_v_broker, 4) if pip_v_broker == pip_v_broker else None,
            "pip_value_per_lot_backtest_hardcoded": pip_v_backtest,
            "mismatch_pct": round(mismatch_pct, 2) if mismatch_pct == mismatch_pct else None,
            "needs_fix": pip_v_broker > 0 and mismatch_pct > 5,
        })

    out_path = out_dir / "symbol_specs.json"
    out_path.write_text(json.dumps(rows, indent=2))
    print(f"\nSaved: {out_path}")

    # Summary
    bugs = [r for r in rows if r.get("needs_fix")]
    print(f"\n{'-'*60}")
    if bugs:
        print(f"FOUND {len(bugs)} pip_value mismatches > 5%:")
        for b in bugs:
            print(f"  - {b['symbol']}: backtest={b['pip_value_per_lot_backtest_hardcoded']:.2f} "
                  f"vs broker={b['pip_value_per_lot_broker_calc']:.4f} "
                  f"({b['mismatch_pct']:.1f}% off)")
        print("\nNext: send symbol_specs.json so I can patch _PIP_VALUE_PER_LOT precisely.")
    else:
        print("All pip_values within 5% of broker. Slippage and parameters are next.")

    # Spread reality check
    print(f"\n{'-'*60}")
    print("Real spreads observed (vs current backtest slippage 0.5 pips):")
    for r in rows:
        sp = r.get("spread_pips_estimate", 0)
        flag = " TOO_LOW" if sp > 1.0 else ""
        print(f"  {r['symbol']:<8} spread ~= {sp:>6.1f} pips{flag}")

    mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
