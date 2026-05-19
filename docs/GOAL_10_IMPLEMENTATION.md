# MT5 Suite /goal 10/10 Implementation

## Current status

The suite is intentionally stopped for audit. Do not restart live-demo trading until Jean approves the next forward-test run.

Operational gate is now implemented and passing; statistical validation gate is intentionally waiting on a clean post-fix sample.

## Functional pieces added

### 1. Audit and scoring

- `scripts/audit_total_strategy.py`
  - Reads active 12 launcher configs.
  - Reads SQLite DBs.
  - Scores every active bot.
  - Writes:
    - `reports/AUDIT_TOTAL_STRATEGY.md`
    - `reports/audit_total_strategy.json`

### 2. /goal checklist gate

- `scripts/suite_goal.py`
  - Validates configs.
  - Optionally runs tests with `--full`.
  - Generates the 10/10 checklist.
  - Writes:
    - `reports/GOAL_10_CHECKLIST.md`
    - `reports/goal_10_checklist.json`

Command:

```powershell
$env:PYTHONPATH='C:\Users\jean_\Desktop\mt5_trading_bot\src'
python scripts\suite_goal.py --full --write
```

### 3. Daily forward report

- `scripts/daily_report.py`
  - Reads all `data/pro*.sqlite` files.
  - Reports PnL, sent orders, slippage, rejects, latest reasons.
  - Writes:
    - `reports/DAILY_FORWARD_REPORT.md`
    - `reports/daily_forward_report.json`

### 4. Risk Engine additions

Added config fields:

- `max_symbol_daily_loss_pct`
- `max_symbol_weekly_loss_pct`
- `max_effective_risk_pct`
- `max_spread_to_sl_ratio`
- `min_sl_atr_ratio`

Applied to active `config/pro*.yaml` files:

- FX:
  - daily symbol loss cap: `0.8%`
  - weekly symbol loss cap: `1.6%`
  - effective risk cap: `0.75%`
  - spread/SL max ratio: `0.20`
  - min SL/ATR ratio: `0.60`
- Metals:
  - daily symbol loss cap: `0.6%`
  - weekly symbol loss cap: `1.2%`
  - effective risk cap: `0.6%`
  - spread/SL max ratio: `0.15`

### 5. Controller workflow

Normal operator workflow should use:

```text
CONTROL_BOTS.bat
```

Do not use `_run_all_pro_autorestart.bat` for normal operation because it still opens 12 visible terminal windows.

## 10/10 definition

The suite cannot honestly be called 10/10 until:

- 20-50 clean post-fix trades per active bot/group exist.
- Metals, FX majors, and JPY crosses are scored separately.
- Profit factor and expectancy are positive on clean data.
- Risk/execution/reporting score remains >= 9.
- No contaminated pre-fix position is mixed into validation.

## Latest gate result

```text
Operational readiness gate: PASS
Validation-to-10 gate: WAITING ON CLEAN SAMPLE
Tests: 28 passed
```
