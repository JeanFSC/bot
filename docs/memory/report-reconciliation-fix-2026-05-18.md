# 2026-05-18 report reconciliation fix

Jean clarified that the concern was the issue affecting reports, not the trade close itself.

## Findings

- `scripts/forward_report.py` counted every row in `position_metrics` as open/floating exposure.
- `position_metrics` keeps telemetry history and was not reconciled when MT5 closed a position.
- Result: stale rows made the report show old open positions/floating PnL even when MT5 had `open_positions=0`.
- `scripts/daily_report.py` summed PnL per SQLite DB, so the same MT5 deal ticket could be counted twice if it was stored in two DBs.
- Current example: XAUUSD TP deal `8274177513` appeared in both `pro_gold.sqlite` and `pro_gold_m5.sqlite`, making total PnL show `18141.56` instead of the unique-ticket total `9070.78` for the 24h window.
- Root cause for future contamination: `_sync_today_deals()` fell back to all same-symbol deals when no exact magic match existed. This let one XAUUSD bot import another XAUUSD bot nonzero-magic deal.

## Changes

- Added `_filter_history_deals_for_bot()` in `src/mt5_bot/cli.py`.
- Deal sync now keeps only same-symbol deals with exact bot magic, plus `magic=0` broker fallback deals.
- `scripts/forward_report.py` now counts active/floating telemetry only when `position_metrics.updated_at` is within the last 15 minutes.
- `scripts/daily_report.py` now calculates total PnL by unique MT5 deal ticket and reports duplicate rows ignored.
- Added `tests/test_deal_sync.py` for the same-symbol/different-magic sync case.

## Verification

- `python -m py_compile src\\mt5_bot\\cli.py scripts\\forward_report.py scripts\\daily_report.py`: PASS
- `python -m pytest -q`: PASS, `29 passed`
- `python scripts\\forward_report.py`: stale `pro.sqlite`, `pro_gbpjpy.sqlite`, and `pro_gold.sqlite` position telemetry no longer appears as current open exposure; all active/floating rows are `0` after watchdog confirmed MT5 `open_positions=0`.
- `python scripts\\daily_report.py`: total PnL is now `9070.78`, unique deal tickets `1`, duplicate deal rows ignored `1`.

## Residual risk

- Existing duplicate rows remain in old SQLite DBs; the daily report now dedupes totals, but per-DB rows can still show contaminated historical deals.
- A deeper cleanup should reconcile existing `deals` and `position_metrics` against MT5 history before using old DBs for formal performance stats.
