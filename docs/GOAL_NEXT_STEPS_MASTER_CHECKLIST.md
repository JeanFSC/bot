# /goal - Master Checklist From Start To Finish

Date: 2026-05-19
Owner/Judge: Bobby
Repo: C:\Users\jean_\Desktop\mt5_trading_bot

## Rule

Every step must end as one of:

- PASS: evidence supports moving forward.
- WAITING: needs clean forward sample, time, or market data.
- BLOCKED: missing input or unsafe to continue.
- FAIL: evidence rejects the idea.

No bot is promoted to live because it sounds good. It must pass data, risk, and operational gates.

## Current Live State

- PASS: reduced suite is running only the current winners.
- Active bots: XAUUSD main, USDCHF, GBPJPY.
- Paused bots stay paused until they pass gates.

## Checklist

### Phase 0 - Protect What Works

- [x] Verify suite is not full 12-bot mode.
- [x] Run only reduced winners.
- [x] Keep XAUUSD main, USDCHF, GBPJPY untouched while healthy.
- [x] Configure 2-hour reports.
- [ ] Continue monitoring for health, drawdown, and expectancy decay.

Status: PASS / ongoing.

### Phase 1 - Build The Evidence Base

- [x] Use corrected trade window from 2026-05-15 onward.
- [x] Use MT5 magic-scoped history as official PnL source.
- [x] Generate status report with PnL, PF, expectancy, avg win/loss.
- [x] Document 33 operational/strategy problems.
- [x] Audit all 12 bots individually.
- [x] Identify that most bots share the same EMA 5/13 M5 template.

Status: PASS.

### Phase 2 - Trading Methodology Upgrade

- [x] Research Fabio-style Auction Market / VWAP / Volume Profile / order-flow concepts.
- [x] Mark Patrick Nill as BLOCKED until Jean provides exact source/handle/spelling.
- [x] Create Methodology V2 standard.
- [x] Define market state, location, confirmation, risk, payoff, and session layers.
- [x] Add market-structure research utilities.

Status: PASS with Patrick source BLOCKED.

### Phase 3 - Research Backtesting

- [x] Add research backtest engine.
- [x] Run paused-bot research backtest on 2026-05-15 to 2026-05-20.
- [x] Run longer research backtest on 2026-04-15 to 2026-05-20.
- [x] Identify USDJPY as only first-pass research candidate.
- [x] Split USDJPY by session.
- [x] Reject Tokyo, NY, and overlap for USDJPY.
- [x] Select USDJPY London as research-only candidate.
- [x] Add setup/session breakdown to reports.
- [x] Add setup-level gates to research report.

Status: PASS.

### Phase 4 - Candidate Design

- [x] Create config/research_usdjpy_london_v2.yaml.
- [x] Keep trade_enabled false.
- [x] Use new magic 260545.
- [x] Restrict to London 7-12 UTC.
- [x] Use conservative risk 0.15%.
- [x] Run London setup/quality breakdown.
- [ ] Recalibrate setup quality scoring because B outperformed A.
- [ ] Validate more history or sandbox sample before live.
- [ ] Decide whether USDJPY London V2 is promoted, kept waiting, or rejected.

Status: WAITING on more evidence.

### Phase 5 - Bot-By-Bot Decisions

- [x] XAUUSD main: keep, do not scale yet.
- [x] USDCHF: keep.
- [x] GBPJPY: keep as low-risk scout, not economically proven.
- [x] USDJPY: redesign candidate, London only.
- [x] USDJPY Asia: fold into USDJPY session work.
- [x] NZDUSD: pause, near but below PF gate.
- [x] GBPUSD: reject current method, payoff problem.
- [x] EURUSD: reject current method.
- [x] USDCAD: pause/no evidence.
- [x] AUDUSD: pause/no evidence.
- [x] XAUUSD_M5: reject current method.
- [x] XAGUSD: pause/no evidence.

Status: PASS.

### Phase 6 - Sandbox Rules

- [x] Add dry-run/sandbox launcher for approved research candidates.
- [x] Candidate may run only with trade_enabled false first.
- [x] Report setup_type, session, market_state, expectancy, PF, avg win/loss.
- [x] Add sandbox signal report for dry-run telemetry.
- [x] Add sandbox report to 2-hour reporting job.
- [x] Create research configs for all paused-bot candidates.
- [x] Validate all research configs: unique magic, unique DB, trade_enabled false.
- [x] Launch all research candidates in dry-run sandbox.
- [x] Fix report counting so wrappers are not counted as trade loops.
- [ ] Require no crash loops and no stale DB/reporting.
- [ ] Require 20-50 clean forward trades before production.

Status: IN_PROGRESS.

### Phase 7 - Promotion Rules

- [ ] Promote only one new bot at a time.
- [ ] Do not return to 12-bot suite until each bot has its own edge.
- [ ] Do not scale low-PnL bots unless risk-adjusted return is meaningful.
- [ ] If a bot cannot produce meaningful return on a 90k account, retire or replace it.

Status: PENDING.

### Phase 8 - Deployment / Main / VPS

- [ ] Keep current branch work unmerged until gates pass.
- [ ] Write migration/runbook updates after methodology stabilizes.
- [ ] Do not push/merge to main without Jean confirmation.
- [ ] VPS only after reduced suite plus any new candidate runs clean.

Status: WAITING.

## Next Immediate Execution

1. Recalibrate USDJPY London V2 quality scoring.
2. Observe next London-session sandbox telemetry.
3. Keep live reduced suite monitored.
