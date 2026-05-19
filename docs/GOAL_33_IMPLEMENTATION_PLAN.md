# MT5 Suite /goal - 33 Problem Implementation Plan

Status legend:

- DONE: implemented or verified with evidence.
- IN_PROGRESS: work started in this goal.
- PENDING: planned but not implemented yet.
- WAITING: requires new forward-test sample or Jean confirmation.
- BLOCKED: cannot proceed safely without missing input.

## Goal

Turn the current MT5 suite from a broad 12-bot experiment into a controlled, auditable forward-test system.

Scope starts from the corrected trade window Jean specified: 2026-05-15 onward. Earlier trades are treated as pre-fix history and excluded from current strategy judgment.

## Operating Decisions

- Source repo for this goal: C:\\Users\\jean_\\Desktop\\mt5_trading_bot.
- Current branch observed: claude/work.
- Suite state when goal started: stopped and verified stopped.
- Do not restart the suite automatically during this goal.
- Do not push or merge to main without Jean's explicit confirmation.
- PnL source of truth: MT5 history filtered by magic.
- SQLite/logs are supporting telemetry, not final PnL authority.

## Bot Policy From 2026-05-15 Audit

Allowed candidates for next reduced forward test:

- USDCHF (config/pro_usdchf.yaml)
- XAUUSD main Gold bot (config/pro_gold.yaml) only with strict risk caps
- GBPJPY (config/pro_gbpjpy.yaml) optional because it is stable but low contribution

Paused until redesigned/retested:

- EURUSD
- GBPUSD
- NZDUSD
- USDCAD
- XAUUSD_M5
- USDJPY
- USDJPY_ASIA
- AUDUSD
- XAGUSD

## The 33 Problems And Fix Plan

### P0 - Critical Operational Blockers

1. Suite must not restart as full 12-bot mode.
   - Status: DONE
   - Fix: create and use a reduced-mode launcher/profile; keep full-suite launcher out of normal workflow.
   - Evidence: START_REDUCED_FORWARD_TEST.bat starts only USDCHF, XAUUSD main, and GBPJPY.

2. Runtime crash loop: NameError: name 'timedelta' is not defined.
   - Status: DONE
   - Fix: current src/mt5_bot/cli.py imports timedelta; historical logs came from an older runtime state.
   - Evidence: from datetime import datetime, time as datetime_time, timedelta, timezone is present in cli.py.

3. PnL/reporting must be magic-scoped.
   - Status: DONE
   - Fix: official reports use MT5 history filtered by magic.
   - Evidence: src/mt5_bot/report_live.py magic map updated to all 12 current bots.

4. Real operating folder vs scratch clone must be fixed.
   - Status: DONE
   - Fix: this goal uses C:\\Users\\jean_\\Desktop\\mt5_trading_bot as source of truth.

5. No robust 2-hour operational report.
   - Status: DONE
   - Fix: scripts/suite_status_report.py now reports process health, MT5 state, magic PnL, critical logs, DB freshness, and OK/DOWN/DEGRADED/DANGEROUS status.
   - Evidence: reports/SUITE_STATUS_REPORT.md and reports/suite_status_report.json generated.

### P1 - Strategy And Methodology Issues

6. EMA 5/13 M5 is too generic across all symbols.
   - Status: PENDING
   - Fix: symbol-specific thresholds and allow-list only for validated bots.

7. Entries are allowed in weak ADX regimes.
   - Status: IN_PROGRESS
   - Fix: reduced candidates now use stricter ADX thresholds: USDCHF 22, GBPJPY 24, XAUUSD 24.

8. Retest and candle confirmation are disabled.
   - Status: PENDING
   - Fix: enable for weak symbols or require alternate confirmation before reactivation.

9. Session filter is too broad (0-24) for most bots.
   - Status: PENDING
   - Fix: add session attribution and restrict weak bots to proven sessions.

10. EURUSD failed post-fix.
    - Status: PENDING
    - Fix: remove from reduced launcher; redesign before re-enable.
    - Evidence: since 2026-05-15, 3 closed trades, 3 losses, -1936.63.

11. GBPUSD has high win rate but negative expectancy.
    - Status: PENDING
    - Fix: pause or reduce; redesign partial/trailing payoff.
    - Evidence: 6W/2L but -433.80.

12. NZDUSD has high win rate but negative expectancy.
    - Status: PENDING
    - Fix: pause or reduce; review payoff and session conditions.

13. USDCAD lacks evidence and is negative.
    - Status: PENDING
    - Fix: keep paused pending more backtest/forward-test evidence.

14. XAUUSD_M5 is not justified.
    - Status: PENDING
    - Fix: keep paused; gold M5 requires separate method.

15. USDJPY / USDJPY_ASIA do not add enough post-fix value.
    - Status: PENDING
    - Fix: pause from reduced launcher until stricter ADX/session rules are tested.

### P1 - Risk Issues

16. Lot sizing is aggressive.
    - Status: DONE
    - Fix: reduced candidates now use lower risk: USDCHF 0.35%, XAUUSD 0.25%, GBPJPY 0.25%.

17. Win rate is masking bad expectancy.
    - Status: DONE
    - Fix: status report now shows PF, expectancy, avg win, and avg loss by magic.

18. Partial close may shrink winners too much.
    - Status: PENDING
    - Fix: compare partial-close vs no-partial by symbol before re-enabling losers.

19. Trailing stop is not solving payoff.
    - Status: PENDING
    - Fix: add MFE/MAE and post-partial outcome reporting.

20. Symbol risk caps are still too loose for validation.
    - Status: DONE
    - Fix: reduced candidates now have lower symbol caps: USDCHF daily/weekly 0.5/1.0, XAUUSD 0.4/0.8, GBPJPY 0.4/0.8.

21. Correlated USD exposure is not blocked hard enough.
    - Status: PENDING
    - Fix: hard-block same-direction USD clusters in reduced mode, not only de-score.

22. Gold needs a separate risk model.
    - Status: DONE
    - Fix: XAUUSD main now has max_order_volume 0.5, risk_pct 0.25, max_effective_risk_pct 0.25, and tighter symbol caps.

### P2 - Data And Analytics Issues

23. Per-bot sample size is too small.
    - Status: WAITING
    - Fix: require at least 30 clean post-fix trades per candidate before declaring edge.

24. Missing attribution by session/regime.
    - Status: PENDING
    - Fix: add session/ADX/RSI/ATR buckets to report.

25. Missing real expectancy ranking.
    - Status: PENDING
    - Fix: rank bots by expectancy, PF, avg win/loss, drawdown, and loss concentration.

26. Error logs count false positives.
    - Status: DONE
    - Fix: scripts/suite_status_report.py excludes MT5 success retcodes 10009 and 10008 from critical log classification.

27. SQLite and MT5 can differ.
    - Status: IN_PROGRESS
    - Fix: MT5 magic-scoped history is official; SQLite gets reconciled as secondary telemetry.

28. No final snapshot before stop/migration.
    - Status: PENDING
    - Fix: add snapshot command for DB/logs/report/commit/config state.

### P2 - Deployment And Operations

29. Not ready to merge to main as production.
    - Status: PENDING
    - Fix: merge only after reduced mode, report script, tests, and runbook pass.

30. Not ready for VPS.
    - Status: PENDING
    - Fix: VPS only after 24h clean reduced run and documented setup.

31. Missing final Codex/IDE runbook.
    - Status: DONE
    - Fix: CODEX_RUNBOOK.md created with source-of-truth, reduced mode, report, stop/start, gate, risk, and VPS rules.

32. Watchdog restart policy is not risk-aware enough.
    - Status: PENDING
    - Fix: watchdog must stop on repeated crash/IPC/db-stale/loss-cap conditions.

33. No formal reduced mode.
    - Status: DONE
    - Fix: START_REDUCED_FORWARD_TEST.bat starts only USDCHF, XAUUSD main, and GBPJPY after live-demo preflight.

## Execution Order

1. Lock source of truth and keep suite stopped.
2. Fix/report runtime blockers.
3. Build reduced mode.
4. Build official 2-hour report.
5. Apply risk/config changes.
6. Add runbook.
7. Run tests and gate scripts.
8. Only then ask Jean for confirmation to restart reduced forward test.

## Current Honest State

IN_PROGRESS. The suite is stopped; no live trading changes have been launched. Completed so far: source-of-truth documentation, full magic-label coverage in report_live.py, reduced launcher, suite status report, reduced risk caps, and Codex runbook.
