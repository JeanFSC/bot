# Suite Checkpoint - 2026-05-18

## Context

Jean asked why the live-demo MT5 suite had not executed new trades after being started.

## Evidence

- `WATCHDOG_SAFE_24H.py --mode live-demo --status --expect-running` showed:
  - `trade_loops=12`
  - `restart_windows=12`
  - account `106490890`
  - balance/equity `91449.18`
  - `open_positions=0`
  - all 12 trade processes running with `--trade-enabled`
- Journals were actively updating in all `data/pro*.sqlite` databases after restart.
- Since `2026-05-18T09:00:00+00:00`, orders count was `0` across the pro databases.
- Journal reasons were mainly:
  - `no_closed_bar_crossover`
  - `trend_filter_blocked_buy`
  - `trend_filter_blocked_sell`
- Logs showed repeated crashes caused by:
  - `NameError: name 'timedelta' is not defined`
  - source: `src/mt5_bot/cli.py`, weekly risk window calculation.

## Change

Fixed `src/mt5_bot/cli.py` by importing `timedelta`:

```python
from datetime import datetime, time as datetime_time, timedelta, timezone
```

## Verification

- `python -m py_compile src/mt5_bot/cli.py` passed.
- `python -m pytest tests/test_risk.py tests/test_executor.py -q` passed: `15 passed`.
- Suite was restarted in live-demo mode.
- Post-restart status showed 12 live trade loops, 12 restart windows, demo account connected, `--trade-enabled` active, and journals updating.

## Interpretation

The suite was not refusing to trade because execution was disabled. It had two causes:

1. Strategy filters were mostly skipping entries because there was no valid closed-bar EMA crossover or the trend filter blocked the direction.
2. A code bug in weekly risk calculation caused intermittent loop crashes/restarts. This is now fixed in source and loaded by restarting the suite.

## Next Check

If no trade occurs after enough market time, inspect whether signal generation is too restrictive for the desired forward-test frequency rather than loosening risk controls blindly.
