# CODEX Handoff

## Git state

- Current branch: `codex/handoff-qa-cleanup`
- Base branch used for the work: `merge/claude-work-to-main`
- Base commit: `1721708326479829818f3795e2ec03a223d49d2a`
- Local `main`: `b3e5d877e1a46767b2d5c41e94385d78a88944fd`
- `origin/main`: `b3e5d877e1a46767b2d5c41e94385d78a88944fd`

### Difference between local `main` and `origin/main`

- At the time of this handoff, `main` and `origin/main` point to the same commit.
- There is no local-vs-remote divergence on `main`.
- The cleanup work is intentionally isolated on `codex/handoff-qa-cleanup`.

## What commit 1721708 already brought into the repo

Real functional content already included in `1721708`:

- Runbooks and operating docs:
  - `CODEX_RUNBOOK.md`
  - `LAPTOP_HANDOFF.md`
  - `docs/BOT_12_INDIVIDUAL_AUDIT.md`
  - `docs/BOT_METHODOLOGY_V2.md`
  - `docs/GOAL_NEXT_STEPS_MASTER_CHECKLIST.md`
- Launchers and watchdog:
  - `START_REDUCED_FORWARD_TEST.bat`
  - `START_RESEARCH_SANDBOX_ALL.bat`
  - `START_SAFE_24H.bat`
  - `WATCHDOG_SAFE_24H.py`
- Research candidate configs:
  - `config/research_*_v2.yaml`
- Reporting/validation scripts:
  - `scripts/suite_status_report.py`
  - `scripts/sandbox_signal_report.py`
  - `scripts/validate_research_candidates.py`
- Runtime/trading support:
  - `src/mt5_bot/cli.py`
  - `src/mt5_bot/executor.py`
  - `src/mt5_bot/mt5_gateway.py`
  - `src/mt5_bot/storage.py`
  - `src/mt5_bot/portfolio_guard.py`
  - `src/mt5_bot/report_live.py`
  - `src/mt5_bot/market_structure.py`
  - `src/mt5_bot/research_strategy.py`
  - `src/mt5_bot/research_backtest.py`

## Files changed in this cleanup branch

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

## Functional changes

### Telegram commander

- `src/mt5_bot/telegram_commander.py`
  - `/start_bots` now starts:
    - reduced live demo
    - research sandbox
  - `/status` now reads the consolidated suite report
  - `/balance` now reports MT5 account values from the consolidated suite report

### Telegram QA

- `qa_telegram.py`
  - no longer assumes 12 active bots
  - validates current commander behavior
  - requires successful `sendMessage`

### Safe/live separation

- All `_restart_*.bat`
  - no longer hardcode `--trade-enabled`
  - now respect config default unless explicit launcher args are passed
- `_run_all_pro_autorestart.bat`
  - now forwards `%*` to restart scripts
- `START_REDUCED_FORWARD_TEST.bat`
  - now passes `--trade-enabled` explicitly to the 3 reduced live bots
- `START_LIVE_DEMO_24H.bat`
  - now passes `--trade-enabled` explicitly to the 12-bot live launcher

### Watchdog

- `WATCHDOG_SAFE_24H.py`
  - counts only real Python trade loops
  - reports live loops and dry-run loops separately
  - in live-demo mode, `--expect-running` accepts valid loop sets for:
    - reduced live suite (`3`)
    - legacy full live suite (`12`)

## Trading / risk impact

- No signal logic, entry rule, stop rule, or sizing formula was changed.
- This cleanup changes orchestration and safety boundaries only.

### Risk reduced

- Safe launchers are safe by default again.
- Live intent is explicit in launchers instead of hidden inside restart scripts.
- Telegram no longer points to the wrong launcher.
- Watchdog status no longer gives false failures under live + sandbox coexistence.

### Risk introduced

- Live behavior now depends on using the correct launcher.
- Manual invocation of `_restart_*.bat` without args is no longer implicitly live.
- This is intentional and documented.

## Tests executed

- `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe -m pytest -q`
  - `37 passed`
- `python qa_mt5_checks.py`
  - `MT5_CHECKS_ALL_OK`
- `python qa_suite_smoke.py`
  - `SMOKE_OK all 12 configs passed MT5 check`
- `python WATCHDOG_SAFE_24H.py --mode live-demo --preflight`
  - `PREFLIGHT_OK`
- `python qa_safe_24h.py`
  - `QA_SAFE_24H_OK`
- `python qa_full_mt5.py`
  - `QA_STATIC_OK`
- `$env:PYTHONPATH='src'; .\.venv\Scripts\python.exe qa_telegram.py`
  - `TELEGRAM_QA_OK`

## Technical explanation of the two failed QA lines and the fix

### `qa_safe_24h.py:55`

- Original problem:
  - The assertion expected the old status command string:
    - `WATCHDOG_SAFE_24H.py --status`
- Actual architecture:
  - `STATUS_SUITE.bat` now uses:
    - `WATCHDOG_SAFE_24H.py --mode live-demo --status --expect-running`
- Why it failed:
  - stale assertion, not a trading runtime bug
- Correct fix:
  - update the QA to validate the current live-demo status invocation
  - update its runtime status call to use the same architecture

### `qa_full_mt5.py:43`

- Original problem:
  - The QA expected:
    - `max_portfolio_open_positions == 5`
- Actual architecture:
  - current configs use tighter guardrails:
    - `max_portfolio_open_positions: 3`
- Why it failed:
  - stale assumption, not config corruption
- Correct fix:
  - update the QA to enforce the real current policy:
    - `0 < max_portfolio_open_positions <= 3`

## Review of report artifacts

- Generated `reports/*.md` and `reports/*.json` files were reviewed.
- They were reverted from the diff.
- Reason:
  - they were execution artifacts produced by scripts during QA
  - they did not represent source-of-truth code changes for this cleanup branch
  - keeping them would mix functional fixes with generated evidence
- The only report intentionally added in this branch is:
  - `docs/reports/CODEX_HANDOFF.md`

## Recommendation on push to main remote

- Push to `main` remote now: **No**

### Condition for saying yes later

- Bobby or Jean reviews and accepts:
  - launcher contract change
  - watchdog expectation change
  - Telegram commander routing change
- Optionally, after one more operational observation window confirms:
  - reduced live suite still behaves normally after a restart
  - research sandbox still remains dry-run only after a restart

## Verification run — 2026-05-19

Second-pass verification executed after the original handoff to confirm nothing drifted.

- Timestamp: `2026-05-19T19:59:00-05:00`
- HEAD unchanged: `286a28978b22304dc4bda9ef1d4a9f93f8a0f27d`
- Working tree: clean

### Results

| QA script | Result |
|---|---|
| `pytest -q` | **37 passed** in 2.81s |
| `qa_mt5_checks.py` | **MT5_CHECKS_ALL_OK** — 12/12 symbols |
| `qa_suite_smoke.py` | **SMOKE_OK** — all 12 configs |
| `WATCHDOG_SAFE_24H.py --mode live-demo --preflight` | **PREFLIGHT_OK** |
| `qa_safe_24h.py` | **QA_SAFE_24H_OK** |
| `qa_full_mt5.py` | **QA_STATIC_OK** |

### Live state at time of check

- live_loops=3, dry_run_loops=8, open_positions=0
- balance=89397.38, recent_log_errors=0
- Journals active: pro_gbpjpy, pro_gold, pro_usdchf

### Conclusion

No regressions. No new failures. Branch is stable and ready for Bobby's review.
Recommendation: **merge to main once Bobby approves**.

---

## How to review or revert

### Review

- `git diff --stat`
- `git diff --name-only`
- `git diff -- WATCHDOG_SAFE_24H.py`
- `git diff -- qa_safe_24h.py`
- `git diff -- qa_full_mt5.py`
- `git diff -- src/mt5_bot/telegram_commander.py`

### Revert only this cleanup branch changes

- `git restore .env.example`
- `git restore START_LIVE_DEMO_24H.bat`
- `git restore START_REDUCED_FORWARD_TEST.bat`
- `git restore WATCHDOG_SAFE_24H.py`
- `git restore _restart_*.bat`
- `git restore _run_all_pro_autorestart.bat`
- `git restore qa_full_mt5.py`
- `git restore qa_safe_24h.py`
- `git restore qa_telegram.py`
- `git restore src/mt5_bot/telegram_commander.py`
- `git restore docs/memory/CODEX_WORKLOG.md`
- `git restore docs/reports/CODEX_HANDOFF.md`
