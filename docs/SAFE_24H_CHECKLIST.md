# SAFE 24H Checklist - MT5 Bot Suite

Purpose: run the 12-bot suite on Jean's PC for forward testing without live trading.

## Safety invariants

- `config/pro*.yaml` must keep `execution.trade_enabled: false`.
- `_restart_*.bat` must not contain `--trade-enabled`.
- `START_SAFE_24H.bat` must run `WATCHDOG_SAFE_24H.py --preflight` before launching.
- Watchdog stops the suite if it detects:
  - active process with `--trade-enabled`,
  - unexpected open MT5 positions,
  - recent ERROR/Traceback/Exception/CRITICAL/NameError in logs.

## Before starting

1. Plug PC to power.
2. Disable Windows sleep/hibernation for the test window.
3. Keep internet stable.
4. Open/log into MT5 demo account.
5. Run:
   - `python qa_safe_24h.py`
   - `python qa_full_mt5.py`
   - `python qa_suite_smoke.py`
   - `python -m pytest -q`

## Start

Double-click or run:

```bat
START_SAFE_24H.bat
```

## Status

Double-click or run:

```bat
STATUS_SUITE.bat
```

Expected healthy state:

- 12 trade loops after startup.
- 12 restart windows.
- `trade_enabled=False` in logs.
- `open_positions=0` during safe mode.
- No recent critical log errors.

## Stop

Double-click or run:

```bat
STOP_SUITE.bat
```

After stop, confirm:

- no `mt5_bot trade` processes,
- no `_restart_*.bat` cmd windows,
- MT5 `open_positions=0`.

## Never do without explicit approval

- Add `--trade-enabled` to any launcher.
- Change configs to `trade_enabled: true`.
- Run this suite on a live account.
- Push repo/remotes with secrets or logs.
