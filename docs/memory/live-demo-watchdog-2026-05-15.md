# Live-demo watchdog fix - 2026-05-15

Context: Jean wanted the MT5 demo suite running with real trade execution (`--trade-enabled`) to observe/fix live demo behavior.

Problem:
- `START_SAFE_24H.bat` left `WATCHDOG_SAFE_24H.py --watch` running in safe mode.
- Safe watchdog treated `--trade-enabled` as DANGER and stopped all 12 bot loops at 2026-05-15T13:26:14Z.
- No positions/trades were open; equity stayed 81347.31.

Fix implemented:
- Added `--mode safe|live-demo` to `WATCHDOG_SAFE_24H.py`.
- Default remains `safe`.
- `live-demo` allows `--trade-enabled` processes and open positions without stopping the suite.
- In `live-demo`, log errors/process-count issues are warnings; suite is left running.
- Added helper BATs:
  - `START_LIVE_DEMO_24H.bat`
  - `STATUS_LIVE_DEMO.bat`

Verification:
- `python -m py_compile WATCHDOG_SAFE_24H.py` passed.
- `python WATCHDOG_SAFE_24H.py --mode live-demo --status --expect-running` reported 12 trade loops and 12 restart windows.
- Started live-demo watchdog with `python WATCHDOG_SAFE_24H.py --mode live-demo --watch --interval 300`.
- MT5 account 106490890 / MetaQuotes-Demo: balance/equity 81347.31, positions 0, pending orders 0 at verification.
