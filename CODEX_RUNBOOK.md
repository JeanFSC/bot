# Codex Runbook - MT5 Reduced Forward Test

## Source Of Truth

Use this repository:

C:\\Users\\jean_\\Desktop\\mt5_trading_bot

Do not use the older scratch clone for live/demo operations unless it has been reconciled.

## Current Operating Rule

The full 12-bot suite is not the default workflow. The next allowed workflow is the reduced forward test:

- USDCHF
- XAUUSD main Gold bot
- GBPJPY optional

The following bots are paused until redesign/retest:

- EURUSD
- GBPUSD
- NZDUSD
- USDCAD
- XAUUSD_M5
- USDJPY
- USDJPY_ASIA
- AUDUSD
- XAGUSD

## Before Any Start

1. Confirm MetaTrader 5 is installed and logged into the demo account.
2. Confirm .env exists locally. Never commit .env.
3. Confirm suite is stopped:

```powershell
python WATCHDOG_SAFE_24H.py --stop
python scripts\\suite_status_report.py --since 2026-05-15 --write
```

Expected stopped state:

- Status: DOWN
- Open positions: 0
- No mt5_bot trade processes.

## Start Reduced Forward Test

Only start after Jean explicitly approves restart.

```powershell
START_REDUCED_FORWARD_TEST.bat
```

This starts only:

- _restart_usdchf.bat
- _restart_gold.bat
- _restart_gbpjpy.bat

## Stop

```powershell
STOP_SUITE.bat
```

Then verify:

```powershell
python scripts\\suite_status_report.py --since 2026-05-15 --write
```

## Two-Hour Report

Run:

```powershell
python scripts\\suite_status_report.py --since 2026-05-15 --write
```

Report files:

- reports/SUITE_STATUS_REPORT.md
- reports/suite_status_report.json

The report status means:

- OK: expected processes, MT5 available, no critical recent logs.
- DOWN: suite stopped.
- DEGRADED: suspicious but not immediately fatal.
- DANGEROUS: MT5 unavailable, critical logs, unexpected process count, or crash-risk state.

## Goal Gate

Run:

```powershell
$env:PYTHONPATH='src'
python scripts\\suite_goal.py --full --write
```

Current honest gate can pass operational readiness, but validation remains WAITING ON CLEAN SAMPLE until enough post-fix reduced-mode trades exist.

## Risk Settings For Reduced Mode

Current reduced candidate caps:

- USDCHF: risk_pct 0.35, max_effective_risk_pct 0.35, daily symbol cap 0.5%.
- XAUUSD main: risk_pct 0.25, max_effective_risk_pct 0.25, max_order_volume 0.5, daily symbol cap 0.4%.
- GBPJPY: risk_pct 0.25, max_effective_risk_pct 0.25, daily symbol cap 0.4%.

## Data Source Rules

- Official PnL: MT5 history filtered by magic number.
- SQLite: telemetry and journal support.
- Logs: runtime health and incident evidence.

Do not judge bot performance from unfiltered SQLite totals alone.

## Migration / VPS Rule

Do not migrate to VPS until:

- Reduced mode runs cleanly for 24h.
- reports/SUITE_STATUS_REPORT.md is clean.
- scripts/suite_goal.py --full --write passes operational gate.
- No repeated crash loops or IPC errors appear.
- Jean confirms the VPS move.
