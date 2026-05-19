# 2026-05-18 timedelta fix and XAUUSD close review

## Scope

Jean asked to fix/recheck the `timedelta` bug and explain why the latest trade closed early.

## timedelta status

- Active repo: `C:\Users\jean_\Desktop\mt5_trading_bot`.
- `src/mt5_bot/cli.py` imports `timedelta` in the datetime import line.
- Verification passed:
  - `.venv\Scripts\python.exe -m py_compile WATCHDOG_SAFE_24H.py src\mt5_bot\cli.py`
  - `.venv\Scripts\python.exe -m pytest -q` -> `28 passed`
- Live-demo watchdog status at review time:
  - `trade_loops=12`
  - `restart_windows=12`
  - `recent_log_errors=0`
  - `open_positions=0`

## XAUUSD trade reconstruction

Evidence source: `data/pro_gold.sqlite`, `logs/bot_gold.log`, and `config/pro_gold.yaml`.

- Position/order: `8661985181`
- Symbol: `XAUUSD`
- Magic: `260436`
- Side: SELL
- Opened: 2026-05-15 13:36:23 Lima
- Initial volume: `7.90`
- Entry request price: `4555.90`
- SL: `4563.62`
- TP: `4540.46`
- Partial close: 2026-05-15 14:10:15 Lima
  - Closed `3.95 / 7.90`
  - Log reason: `Partial close: ticket=8661985181 profit_pips=382.0 vol_close=3.95/7.90`
  - Config reason: `use_partial_close: true`, `partial_close_ratio: 0.5`, trigger uses `breakeven_atr_multiplier`.
- Final close: 2026-05-17 20:01:30 Lima
  - Closed remaining `3.95`
  - MT5 deal comment: `[tp 4540.46]`
  - Profit: `9088.95`
  - Swap: `-18.17`

## Conclusion

The final trade did not close early by bot panic, watchdog, manual action, or time stop. It closed at the configured TP.

The earlier-looking close was an intentional partial TP1: the bot is configured to close 50% once the position reaches the ATR-based partial-close trigger. That behavior is planned in the current config.

## Follow-up risk note

There were `watchdogs=2` in the status output. That is not the cause of this trade close, but it is operationally untidy and should be cleaned up in a separate watchdog/process hygiene pass if it persists.
