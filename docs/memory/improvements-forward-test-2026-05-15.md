# Improvements + forward-test state — 2026-05-15

Implemented while operating the live-demo MT5 suite.

## Code/config changes
- Added config fields:
  - `max_trades_per_symbol_per_hour`
  - `max_position_minutes`
  - `time_stop_min_profit_pips`
- Added per-symbol hourly entry throttle in `TradeExecutor` via `BotStorage.get_sent_order_count_since(...)`.
- Added persistent `position_metrics` table for open-position telemetry:
  - current pips/profit
  - MFE/MAE pips
  - MFE/MAE profit
- Added order-result migrations:
  - `result_price`
  - `slippage_pips`
- Added slippage logging/journal context; fixed MetaTrader5 result `price=0.0` handling so slippage is left null instead of recording impossible values.
- Added `TradeExecutor.record_position_metrics()` and `TradeExecutor.manage_time_stops()`.
- CLI now runs telemetry/time-stop management during both active and idle cycles.
- Added `scripts/forward_report.py` for per-DB forward-test summaries.
- Patched `risk._pip_value_per_lot()` to use contract-size value as a conservative floor because MetaQuotes demo reports XAUUSD/XAGUSD tick values too low by ~10x. This prevents oversized future metals positions.
- Added test coverage for XAUUSD underreported tick value sizing.

## Config guardrails applied to pro configs
- `max_trades_per_symbol_per_hour: 3`
- `max_position_minutes: 45`
- `time_stop_min_profit_pips: 0.0`
- `max_loss_per_symbol_per_hour_pct: 0.8`
- portfolio caps kept tight (`max_portfolio_open_positions <= 3`, `max_same_currency_positions <= 2`).

## Verification
- `python -m py_compile src\\mt5_bot\\risk.py src\\mt5_bot\\storage.py src\\mt5_bot\\executor.py src\\mt5_bot\\cli.py scripts\\forward_report.py` passed.
- `python -m pytest -q` passed: `26 passed`.
- Suite restarted after changes and status showed:
  - 12 trade loops
  - 12 restart windows
  - all 12 with `--trade-enabled`
  - account `106490890 / MetaQuotes-Demo`
  - live-demo mode accepts open positions.

## Critical observation
- Before the metals sizing fix was applied, XAUUSD opened a SELL `7.90` lots at `4555.97`, SL `4563.62`, TP `4540.46`, magic `260436`.
- This was much larger than intended because broker `trade_tick_value` for XAUUSD appears underreported vs contract-size cash value.
- After the fix, future XAU/XAG position size should be around `0.8` lots for similar risk/SL instead of `7.9` lots.
- Existing open position remains live and was fluctuating around -$1.3k at last check. Needs explicit decision: leave demo trade to time-stop/SL/TP, close manually, or reduce exposure if supported.

## Latest recommendation
- Do not call the suite fully healthy until the oversized legacy XAUUSD position is handled.
- Future entries are safer after the risk sizing patch, but the current position still carries pre-fix size risk.
