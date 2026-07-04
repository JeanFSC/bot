# MT5 Fabble Plan Implementation - 2026-07-02

## Context

Jean paused the autonomous MT5 entry agent after recent demo losses showed a payoff skew: many small winners were not covering occasional full-SL losses. Fabble's quant/risk review identified two immediate blockers before re-enabling entries:

- Dynamic position management was duplicated between the trade loop and the action-enabled live supervisor.
- SQLite used the default journal mode while multiple processes could write runtime/ledger events.

The entry stack remained paused during this patch. No manual trade open, close, or modification was performed.

## Implemented

### Phase 0 - Operational Safety

- Added `dynamic_management_owner`.
  - Default remains `trade_loop` for backward compatibility.
  - Active autonomous demo configs now set `dynamic_management_owner: supervisor`.
  - When supervisor owns dynamic management, `cli.py` records position telemetry but skips no-favorable-excursion exits, time stops, winner scaling, profit lock, partial close, and trailing management.
- Kept supervisor as the single dynamic-management owner for paused/demo execution.
- Enabled SQLite write hardening in `BotStorage`:
  - `PRAGMA journal_mode=WAL`
  - `PRAGMA synchronous=NORMAL`
  - `PRAGMA busy_timeout=30000`
  - connection `timeout=30.0`

### Phase 1 - Payoff Stabilization

- Adjusted active autonomous configs:
  - `profit_lock_trigger_rr: 0.50`
  - `profit_lock_retrace_rr: 0.45`
  - `breakeven_trigger_rr: 0.50`
  - `partial_close_trigger_rr: 0.50`
  - `adx_min_value: 22`
  - `use_atr_percentile_filter: true`
  - `atr_percentile_lookback: 100`
  - `atr_min_percentile: 30.0`
- Added R-based trigger support for:
  - breakeven stop movement
  - partial close eligibility
- Added ATR percentile gate to block entries when current ATR is below the configured rolling percentile for that symbol.
- Kept `risk_pct` at `0.35` as recommended by Fabble; the patch targets expectancy and execution structure, not smaller nominal bets.
- Removed XAU/XAG from active autonomous execution list; they remain research-only.

## Active Configs After Patch

- `config/pro_usdchf.yaml`
- `config/pro_audusd_m5_aggressive.yaml`
- `config/pro_gbpjpy.yaml`
- `config/pro_usdjpy_m5_safe.yaml`
- `config/pro_eurusd_m5_aggressive.yaml`
- `config/pro_gbp_m5_aggressive.yaml`
- `config/pro_nzdusd_m5_aggressive.yaml`
- `config/pro_usdcad.yaml`

## Verification

- Targeted tests: `49 passed`
- Full test suite: `147 passed`
- Preflight: `AGENT_PREFLIGHT_OK configs=8`

## Operating State

- Entry agent should remain paused until Jean explicitly asks to reactivate it.
- Portfolio heat and action-enabled supervisor may stay running to supervise existing open demo exposure.
- Next reactivation should be treated as a clean 50-trade experiment with frozen parameters.

## Validation Gates For Next 50 Trades

- Profit factor `>= 1.30`
- Avg win / avg loss `>= 0.35`
- Expectancy `>= +0.25 USD/trade`
- Track percentage of losers saved by breakeven
- Invalidate or rollback if:
  - PF `< 0.90` after 30 post-patch trades
  - 3 full-SL losses in 24h without touching breakeven first
  - win rate drops below `80%`

