# CODEX Worklog

## Session

- Timestamp: `2026-05-19T18:16:01.4931033-05:00`
- Base branch: `merge/claude-work-to-main`
- Current branch: `codex/handoff-qa-cleanup`
- Base commit: `1721708326479829818f3795e2ec03a223d49d2a`
- Main local commit: `b3e5d877e1a46767b2d5c41e94385d78a88944fd`
- origin/main commit: `b3e5d877e1a46767b2d5c41e94385d78a88944fd`

## Task objective

- Close the handoff cleanly.
- Leave the repo reviewable.
- Keep the live reduced suite and the research sandbox running in the architecture expected by the repo.
- Add audit evidence without leaking secrets.

## Files touched

- `.env.example`
- `START_LIVE_DEMO_24H.bat`
- `START_REDUCED_FORWARD_TEST.bat`
- `WATCHDOG_SAFE_24H.py`
- `_restart_aud.bat`
- `_restart_eurusd.bat`
- `_restart_gbpjpy.bat`
- `_restart_gbpusd.bat`
- `_restart_gold.bat`
- `_restart_gold_m5.bat`
- `_restart_jpy.bat`
- `_restart_jpy_asia.bat`
- `_restart_nzdusd.bat`
- `_restart_silver.bat`
- `_restart_usdcad.bat`
- `_restart_usdchf.bat`
- `_run_all_pro_autorestart.bat`
- `qa_full_mt5.py`
- `qa_safe_24h.py`
- `qa_telegram.py`
- `src/mt5_bot/telegram_commander.py`
- `docs/memory/CODEX_WORKLOG.md`
- `docs/reports/CODEX_HANDOFF.md`

## Assumptions

- The current repo expects two parallel operating layers:
  - reduced live demo
  - research sandbox dry-run
- Research configs must keep `trade_enabled: false`.
- Demo account only. No real account usage.
- Telegram must use a real user or group chat id, never the bot id.

## Risks

- The reduced live suite can open demo trades.
- Telegram command `/start_bots` can affect running processes.
- Launchers that hardcode `--trade-enabled` break the safe/live separation and are dangerous.
- Running research outside session hours produces `WAITING`; that is not a runtime failure.

## What commit 1721708 already contains

Observed from `git show --stat --summary 1721708326479829818f3795e2ec03a223d49d2a`.

Real functional changes already present in that commit include:

- Runbooks and operating docs:
  - `CODEX_RUNBOOK.md`
  - `LAPTOP_HANDOFF.md`
  - multiple `docs/*` and `docs/memory/*`
- New launchers and watchdog layer:
  - `START_REDUCED_FORWARD_TEST.bat`
  - `START_RESEARCH_SANDBOX_ALL.bat`
  - `START_SAFE_24H.bat`
  - `STATUS_SUITE.bat`
  - `STOP_SUITE.bat`
  - `WATCHDOG_SAFE_24H.py`
- Research configs:
  - `config/research_*_v2.yaml`
- Reporting and validation scripts:
  - `scripts/suite_status_report.py`
  - `scripts/sandbox_signal_report.py`
  - `scripts/validate_research_candidates.py`
  - several other scripts under `scripts/`
- Trading/runtime code:
  - `src/mt5_bot/cli.py`
  - `src/mt5_bot/executor.py`
  - `src/mt5_bot/mt5_gateway.py`
  - `src/mt5_bot/storage.py`
  - `src/mt5_bot/portfolio_guard.py`
  - `src/mt5_bot/report_live.py`
  - `src/mt5_bot/market_structure.py`
  - `src/mt5_bot/research_strategy.py`
  - `src/mt5_bot/research_backtest.py`

## Changes executed in this session

### 1) Telegram commander aligned to current architecture

- Problem solved:
  - `src/mt5_bot/telegram_commander.py` was pointing at the legacy 12-bot launcher.
- Change:
  - `/start_bots` now launches:
    - `START_REDUCED_FORWARD_TEST.bat`
    - `START_RESEARCH_SANDBOX_ALL.bat`
  - `/status` and `/balance` now read operational state from `scripts/suite_status_report.py`.
- Risk reduced:
  - Prevents accidental restart of the wrong suite from Telegram.

### 2) Telegram QA aligned to current suite model

- Problem solved:
  - `qa_telegram.py` assumed 12 active bots.
- Change:
  - It now validates the current model and requires:
    - valid bot token
    - valid chat destination
    - real `sendMessage`
- Risk reduced:
  - Avoids false green when token works but chat target is invalid.

### 3) Safe/live separation fixed in launchers

- Problem solved:
  - All `_restart_*.bat` files hardcoded `--trade-enabled`.
  - That made safe-mode QA fail and weakened the launcher contract.
- New rule:
  - Restart scripts are safe by default.
  - Live mode is enabled explicitly by launchers via `%*`.
- Files changed:
  - all `_restart_*.bat`
  - `_run_all_pro_autorestart.bat`
  - `START_REDUCED_FORWARD_TEST.bat`
  - `START_LIVE_DEMO_24H.bat`
- Risk reduced:
  - Safe launchers now stay safe.
  - Live launchers now declare live intent explicitly.
- Risk introduced:
  - Live behavior now depends on correct launcher usage.
  - Manual direct execution of `_restart_*.bat` no longer implies live trading.

### 4) Watchdog status logic aligned to live + sandbox coexistence

- Problem solved:
  - `WATCHDOG_SAFE_24H.py` used stale expectations for `--expect-running`.
  - It also counted wrapper processes as trade loops.
- New rule:
  - Trade loops count only real Python trading processes.
  - In live-demo mode, valid expected live loop counts are `3` or `12`.
  - Dry-run loops are reported separately.
- Risk reduced:
  - Status no longer reports false failure when live reduced and sandbox run together.

### 5) QA fixes

- `qa_safe_24h.py`
  - Updated to validate the current `STATUS_SUITE.bat` invocation:
    - `--mode live-demo`
    - `--status`
    - `--expect-running`
  - Updated watchdog status execution to match current architecture.
- `qa_full_mt5.py`
  - Updated the stale guard from `max_portfolio_open_positions == 5`
    to `0 < max_portfolio_open_positions <= 3`.
  - This matches current guardrail docs and configs.

## Report artifacts review

- Generated `reports/*.md` and `reports/*.json` artifacts were reviewed.
- They were reverted from the diff because they were execution artifacts, not functional source changes.
- They were not deleted from the repo history and were not removed silently.
- Reason:
  - keep the handoff diff focused on functional code + audit docs
  - avoid mixing generated evidence with code fixes in this cleanup branch

## Commands executed and summarized results

### Git baseline

- `git status --short`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git rev-parse origin/main`
- `git rev-parse main`

### Required validations

- `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q`
  - Result: `37 passed`
- `python qa_mt5_checks.py`
  - Result: `MT5_CHECKS_ALL_OK`
- `python qa_suite_smoke.py`
  - Result: `SMOKE_OK all 12 configs passed MT5 check`
- `python WATCHDOG_SAFE_24H.py --mode live-demo --preflight`
  - Result: `PREFLIGHT_OK`
- `python qa_safe_24h.py`
  - Result: `QA_SAFE_24H_OK`
- `python qa_full_mt5.py`
  - Result: `QA_STATIC_OK`

### Additional validations

- `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe qa_telegram.py`
  - Result: `TELEGRAM_QA_OK`
- `python scripts\validate_research_candidates.py`
  - Result: all research configs `PASS`
- `python scripts\suite_status_report.py --since 2026-05-15 --write`
  - Result seen during session: `Status: OK`, `3` live loops, `8` dry-run loops

## What failed during the session

- `qa_safe_24h.py:55`
  - Failure cause:
    - static assertion expected the old status command string
  - Resolution:
    - assertion updated to current launcher architecture
- `qa_full_mt5.py:43`
  - Failure cause:
    - stale assumption `max_portfolio_open_positions == 5`
  - Resolution:
    - aligned to current guardrail policy `<= 3`
- Additional bug found:
  - `_restart_*.bat` hardcoded `--trade-enabled`
  - fixed by making live intent explicit in launchers instead of restarts

## Pending

- No functional blocker remains for this cleanup branch.
- Main remote should still wait for review of:
  - launcher contract changes
  - watchdog expectation changes
  - Telegram commander changes

## Final state before commit

- Branch: `codex/handoff-qa-cleanup`
- Working tree intentionally contains only:
  - launcher/watchdog/QA fixes
  - Telegram commander/QA updates
  - audit markdown files

---

## Verification Session — 2026-05-19

- Timestamp: `2026-05-19T19:59:00-05:00`
- Current branch: `codex/handoff-qa-cleanup`
- HEAD: `286a28978b22304dc4bda9ef1d4a9f93f8a0f27d`
- origin/main: `b3e5d877e1a46767b2d5c41e94385d78a88944fd`
- Working tree at session start: clean (no uncommitted changes)

### Objective

Confirm the branch is ready for Bobby's review and eventual merge to main.
No code changes intended — verification and audit doc update only.

### Files reviewed/touched

- `docs/memory/CODEX_WORKLOG.md` (this file — audit entry added)
- `docs/reports/CODEX_HANDOFF.md` (verification section added)

### Commands executed and results

| Command | Result |
|---|---|
| `git status --short` | (clean) |
| `git branch --show-current` | `codex/handoff-qa-cleanup` |
| `git rev-parse HEAD` | `286a28978b22304dc4bda9ef1d4a9f93f8a0f27d` |
| `git rev-parse origin/main` | `b3e5d877e1a46767b2d5c41e94385d78a88944fd` |
| `git diff --stat origin/main...HEAD` | 157 files changed, 11671 ins, 260912 del |
| `pytest -q` | `37 passed in 2.81s` |
| `python qa_mt5_checks.py` | `MT5_CHECKS_ALL_OK` (12/12 symbols OK) |
| `python qa_suite_smoke.py` | `SMOKE_OK all 12 configs passed MT5 check` |
| `python WATCHDOG_SAFE_24H.py --mode live-demo --preflight` | `PREFLIGHT_OK mode=live-demo` |
| `python qa_safe_24h.py` | `QA_SAFE_24H_OK` |
| `python qa_full_mt5.py` | `QA_STATIC_OK` |

### Watchdog live status observed during QA

- trade_loops=11, live_loops=3, dry_run_loops=8
- account balance=89397.38, equity=89397.38, open_positions=0
- 3 live PIDs confirmed with `--trade-enabled`
- recent_log_errors=0
- Journals: pro_gbpjpy, pro_gold, pro_usdchf active

### Verdict

All QA green. No regressions detected. No code changes needed.
Branch is ready for Bobby's review.
