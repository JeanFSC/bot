# MT5 Suite Deep Audit - 2026-05-18

Scope: live-demo suite status, reports, trade accounting, stale telemetry, execution safety, logs, validation gates.

## Current Gate

- Timestamp checked: 2026-05-18 ~08:14 Lima / 13:14 UTC.
- Test gate: PASS, `29 passed`.
- Status gate: running live-demo, `trade_loops=12`, `open_positions=0`, `recent_log_errors=0`.
- Account observed by status: `106490890`, balance/equity `91451.16 / 91451.16`.
- No close/modify/restart action was executed.

## P0 / Immediate Operational Mismatch

### Suite is running, not stopped

Evidence:

- `STATUS_SUITE.bat` reports `--trade-enabled active as expected in live-demo`.
- Active bot processes:
  - `config/pro.yaml`
  - `config/pro_gbp.yaml`
  - `config/pro_jpy.yaml`
  - `config/pro_gold.yaml`
  - `config/pro_aud.yaml`
  - `config/pro_usdchf.yaml`
  - `config/pro_gold_m5.yaml`
  - `config/pro_usdcad.yaml`
  - `config/pro_nzdusd.yaml`
  - `config/pro_jpy_asia.yaml`
  - `config/pro_gbpjpy.yaml`
  - `config/pro_silver.yaml`

Impact:

- The scheduled preflight said to re-check before advising and referenced suite stopped/restart only from `CONTROL_BOTS.bat`.
- Actual state is live-demo running. This is not automatically bad, but it is a control-state mismatch.

Recommendation:

- Before any live restart/stop/modify decision, explicitly ask Jean.
- Treat the current run as active live-demo unless Jean confirms it should be stopped.

## P1 / Report Accuracy

### GBPJPY trade is not counted in daily report

Evidence:

- `data/pro_gbpjpy.sqlite` has two sent orders since 2026-05-17:
  - entry order `8675370420`, local result deal `8288142529`, volume `0.07`, price `212.365`.
  - partial close order `8675552771`, local result deal `8288350521`, volume `0.04`, fill `212.424`.
- `data/pro_gbpjpy.sqlite` currently has `deals=0`.
- `scripts/daily_report.py` only sums rows from `deals`, so it shows `pro_gbpjpy.sqlite | PnL 0.00 | Deals 0 | Orders 2`.
- Live MT5 history query during this audit returned only XAUUSD deal `8274177513`, not the GBPJPY deal records.

Impact:

- Daily report misses the small GBPJPY realized profit Jean asked about.
- Order table proves the bot sent/managed the trade, but the realized PnL ledger is incomplete.

Recommendation:

- Add a reconciliation check: every successful send order with a nonzero MT5 deal id must eventually appear in `deals` or be flagged as `missing_deal_sync`.
- Do not infer official PnL from `orders.result_json` as the primary ledger; use it as an audit fallback/alert.

### XAUUSD TP deal is still duplicated across two DBs

Evidence:

- Ticket `8274177513` appears in both `pro_gold.sqlite` and `pro_gold_m5.sqlite`.
- `scripts/daily_report.py` now dedupes total PnL by ticket, so total shows `9070.78`, not `18141.56`.
- Per-DB rows still show both gold DBs with `9070.78`.

Impact:

- Aggregate total is fixed, but per-bot reporting remains misleading.
- Strategy evaluation can still over-credit the wrong bot unless the analysis dedupes by ticket and position id.

Recommendation:

- Keep aggregate dedupe.
- Add a duplicate-ticket section to the markdown report, listing source DBs.
- Fix sync ownership so `pro_gold_m5.sqlite` does not import `magic=260436` XAUUSD deals from `pro_gold.yaml`.

## P1 / Stale Position Telemetry

### Closed positions remain in `position_metrics`

Evidence:

- `pro_gold.sqlite.position_metrics` still contains XAUUSD ticket `8661985181` even though MT5 reports `open_positions=0`.
- `pro_gbpjpy.sqlite.position_metrics` still contains GBPJPY ticket `8675370420` even though MT5 reports `open_positions=0`.
- `pro.sqlite.position_metrics` still contains EURUSD ticket `8662680653` from 2026-05-15.
- `storage.record_position_metrics()` upserts open positions but does not delete/mark positions that disappeared from MT5.

Impact:

- Any report that reads `position_metrics` without a recent `updated_at` cutoff can show false open exposure or stale floating PnL.
- `forward_report.py` currently filters to the last 15 minutes, which avoids the worst false positive, but the underlying data remains dirty.

Recommendation:

- Add a cleanup/snapshot step: after reading current MT5 positions, delete or mark stale rows not present in the current position ticket set.
- Prefer `closed_at` / `is_open` fields over silently retaining closed rows.

## P2 / Status/Watchdog Clarity

### `watchdogs=2` can be a status self-count artifact

Evidence:

- Direct process enumeration showed one persistent watchdog process:
  - `WATCHDOG_SAFE_24H.py --mode live-demo --watch --interval 300`
- When `STATUS_SUITE.bat` runs, it launches `WATCHDOG_SAFE_24H.py --mode live-demo --status --expect-running`.
- The status run can count itself, producing `watchdogs=2`.
- A direct import check reported `watchdog 1`.

Impact:

- This can create a false duplicate-watchdog concern.

Recommendation:

- Exclude `--status` command lines from `watchdog_processes()`.

### `restart_windows=12` is expected for current launcher design

Evidence:

- There are 12 `cmd.exe /c _restart_*.bat` windows, one per active bot.
- Each owns one trade loop.

Impact:

- Not automatically a defect, but noisy.

Recommendation:

- Longer term: central controller should own the processes and expose status, to avoid relying on many restart windows.

## P2 / Historical / Contaminated Data

### Historical XAUUSD order slippage is nonsensical

Evidence:

- `pro_gold.sqlite.orders` has XAUUSD entry order `8661985181` with result price `0.0` and slippage `455589.99` pips.
- The order was also part of the known pre-fix metals sizing problem.

Impact:

- Any slippage average that includes this row is invalid.
- It should be excluded from clean validation.

Recommendation:

- Treat historical metals pre-fix rows as contaminated.
- Report validation separately for clean post-fix trades.

## Execution Quality

### Latest GBPJPY trade behavior

Evidence:

- Logs show `Signal=BUY reason=ema_cross_above`.
- Entry: `0.07` lots at `212.365`.
- Partial close: `0.04` at approximately `212.424`, retcode `10009`.
- Trailing stop update: old SL `212.27000`, new SL `212.39100`, retcode `10009`.
- MT5 account later shows `open_positions=0`.

Conclusion:

- Execution behavior was aligned with current config: partial close + trailing/breakeven.
- The issue is not the trade logic; it is post-trade ledger/report reconciliation.

## Validation Outputs

- `pytest -q`: PASS, `29 passed`.
- `scripts/daily_report.py`: total PnL `9070.78`, duplicate deal rows ignored `1`, sent orders `2`, rejected attempts `0`.
- `scripts/forward_report.py`: active telemetry `0` across all DBs because recent cutoff excludes stale position rows.
- `scripts/advanced_validation.py`: functional but `WAITING_OR_FAIL` for groups due insufficient/contaminated sample.

## Recommended Fix Order

1. Add deal-sync reconciliation warning for successful orders with deal IDs missing from `deals`.
2. Add stale `position_metrics` cleanup/closed marking.
3. Fix duplicate same-symbol deal ownership so gold M5 does not import gold M15/M5 sibling magic.
4. Fix watchdog status self-count.
5. Keep all strategy validation in WAITING until enough clean post-fix trades exist.

## Current Bottom Line

The live-demo suite is not showing execution errors right now. The dangerous part is reporting/telemetry accuracy: it can undercount GBPJPY, duplicate XAUUSD per DB, and keep closed positions as stale rows. Do not scale or judge strategy performance from the current reports until those reconciliation issues are fixed.

## Fix Applied - 2026-05-18 08:24 Lima

- Updated deal sync filtering to require exact magic for same-symbol bot ownership. This prevents a sibling XAUUSD bot from importing another bot\'s nonzero-magic deal.
- Updated `daily_report.py` to show missing synced deal tickets and duplicate deal-ticket sources.
- Removed stale `position_metrics` rows for closed EURUSD, XAUUSD, and GBPJPY tickets after verifying MT5 `open_positions=0`.
- Removed duplicated current-window XAUUSD TP deal `8274177513` from `data/pro_gold_m5.sqlite`; backup saved at `data/pro_gold_m5.sqlite.backup_before_magic_cleanup_20260518_0824`.
- Updated `WATCHDOG_SAFE_24H.py` so `--status` runs no longer count themselves as persistent watchdogs.

Validation after fix:

- `pytest -q`: `30 passed`.
- `daily_report.py`: total PnL `9070.78`, duplicate deal rows `0`, missing GBPJPY sync tickets `8288142529` and `8288350521`.
- `WATCHDOG_SAFE_24H.py --mode live-demo --status --expect-running`: `trade_loops=12`, `watchdogs=1`, `open_positions=0`, `recent_log_errors=0`.

Remaining issue:

- GBPJPY order results still have missing synced deals in MT5/local deal ledger. The report now flags them instead of silently showing a clean `0.00`, but official PnL should not be inferred from the order table alone.

## Restart Applied - 2026-05-18 10:35 Lima

Jean confirmed applying the recommendation after the account was flat.

Actions:

- Verified `open_positions=0` before restart.
- Stopped the live-demo suite processes with `WATCHDOG_SAFE_24H.py --mode live-demo --stop`.
- Stopped the old persistent watchdog process.
- Removed the reinserted current-window XAUUSD duplicate from `data/pro_gold_m5.sqlite`; backup saved at `data/pro_gold_m5.sqlite.backup_before_restart_cleanup_20260518_1035`.
- Relaunched live-demo watchdog and the 12-bot autorestart suite.

Post-restart validation:

- `WATCHDOG_SAFE_24H.py --mode live-demo --status --expect-running`: `trade_loops=12`, `restart_windows=12`, `watchdogs=1`, `open_positions=0`, `recent_log_errors=0`.
- New process ids observed: `20940,20900,20920,21136,21156,21208,21348,21268,21236,21284,21304,21300`.
- `pytest -q`: `30 passed`.
- `daily_report.py`: total PnL `9072.76`, unique deal tickets `4`, duplicate deal rows `0`, missing synced deal tickets `6`.

Remaining issue after restart:

- Deal-sync gaps remain flagged by the report for `pro_gbp.sqlite`, `pro_gbpjpy.sqlite`, `pro_jpy.sqlite`, and `pro_usdchf.sqlite`. This is now visible and should be the next reporting fix before performance conclusions.

## Deal Sync Forward-Window Fix - 2026-05-18 10:52 Lima

Root cause:

- MT5 history queries using local/UTC `now` did not return all recent broker deals.
- Querying the same window with a small future buffer returned the missing tickets. The likely cause is broker/server timestamp skew ahead of local UTC.

Code fix:

- Updated `src/mt5_bot/cli.py` so today deal sync queries MT5 through `now + 6h`.
- Kept exact symbol + exact magic filtering so sibling bots cannot import each other's deals.

One-time reconciliation:

- Inserted missing EURUSD, GBPUSD, USDJPY, GBPJPY, and USDCHF deals into their owner SQLite ledgers.
- No open position was present before restart.

Post-fix validation:

- `scripts/daily_report.py`: total PnL `8039.79`, unique deal tickets `16`, duplicate rows `0`, missing synced deal tickets `0`.
- `pytest -q`: `30 passed`.
- Restarted live-demo suite after Jean's confirmation.
- `WATCHDOG_SAFE_24H.py --mode live-demo --status --expect-running`: `trade_loops=12`, `restart_windows=12`, `watchdogs=1`, `open_positions=0`, `recent_log_errors=0`.

Operational conclusion:

- Reporting/ledger reconciliation is clean for the current window after this fix.
- Strategy quality is still `WAITING`: do not scale based only on today's corrected ledger; collect clean forward trades and review risk/drawdown behavior.
