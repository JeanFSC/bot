# Architecture

## Overview

This repo runs an MT5 demo trading agent with a risk-first operating model.
The current production-like path is the autonomous demo agent:

`MT5_AGENT.bat watchdog-bg`

That starts `mt5_bot.agent_watchdog`, which starts `mt5_bot.agent_runner`,
which rotates through the configs listed in `config/autonomous_agent.yaml`.
The current active configs are:

- `config/pro_usdchf.yaml`
- `config/pro_gold.yaml`
- `config/pro_gbpjpy.yaml`

The agent is demo-only unless a caller explicitly passes the approved demo
order flag. Do not use old full-suite launchers unless a current runbook says
they are the intended path.

## Official Launcher

Use `MT5_AGENT.bat` for the autonomous demo agent:

- `preflight`: validate active agent configs.
- `watchdog`: foreground watchdog for manual operation.
- `watchdog-bg`: service/task style watchdog with logs redirected.
- `maintenance`: local reports, backup, experiment snapshots, optional notify.
- `maintenance-bg`: maintenance with logs redirected.
- `replay-30d`: replay/backtest evidence report.
- `process-guard`: duplicate trade process audit.
- `paper-once`: one agent pass without demo order permission.
- `demo-once`: one agent pass with demo order permission.

Legacy `START_*.bat`, `_restart_*.bat`, and old suite BATs may still exist for
research or older runbooks. Treat them as legacy unless this document or a
current handoff explicitly names them.

## Core Components

- `mt5_bot.agent_watchdog`: health gate and process supervisor. It checks MT5
  account/terminal permissions, stale journals, floor equity, and starts/stops
  the child agent only when health allows it.
- `mt5_bot.agent_runner`: autonomous rotation over the configured symbols,
  learning phase, and demo-order guard.
- `mt5_bot.cli`: one-symbol trade loop. It fetches rates, computes signals,
  applies runtime risk gates, manages open positions, writes journals, and
  calls the executor.
- `mt5_bot.strategy`: EMA crossover signal engine with trend, RSI, ATR, ADX,
  session, and optional retest/candle filters.
- `mt5_bot.executor`: order checks/sends, risk firewall, SL/TP, partial close,
  trailing stop, time stop, and order result persistence.
- `mt5_bot.storage`: SQLite persistence for account snapshots, signals,
  orders, deals, trade journal, runtime events, and risk state.
- `mt5_bot.autonomous_agent`: setup memory, confidence scoring, risk multiplier
  learning, and setup-level allow/block/reduce decisions.
- `mt5_bot.news_filter`: high-impact economic calendar filter. Missing calendar
  data defaults to fail-closed and blocks entries unless `MT5_NEWS_FAIL_MODE`
  is explicitly set to `open`.
- `mt5_bot.portfolio_guard`: portfolio exposure and correlation/theme guard.
- `mt5_bot.process_guard`: detects duplicate `mt5_bot trade --config ...`
  process groups.
- `mt5_bot.maintenance`: reports, backups, experiment snapshots, process audit,
  postmortem sync, and optional notification.
- `mt5_bot.replay`: replay/backtest report generator for configured symbols.
- `mt5_bot.notifier`: non-blocking Telegram notification helper.

## Data Flow

1. Watchdog collects MT5 health and journal freshness.
2. If healthy, watchdog starts agent runner.
3. Runner selects one config at a time from `config/autonomous_agent.yaml`.
4. The trade loop connects to MT5 and validates demo account/permissions.
5. Rates are loaded from MT5 for the signal timeframe and trend timeframe.
6. Strategy emits `BUY`, `SELL`, or `NONE` with a reason.
7. Runtime gates check spread, news, session, equity, drawdown, loss limits,
   open positions, portfolio overlap, and memory confidence.
8. Executor performs broker-side order checks and sends only if all gates pass.
9. Storage records account, signal, runtime events, journal rows, orders, and
   deals.
10. Maintenance/replay consume SQLite data and write reports.

## Data Stores

- `data/*.sqlite`: per-symbol trading DBs.
- `data/autonomous_agent_memory.sqlite`: setup-level learning memory.
- `data/watchdog_health.jsonl`: watchdog health history.
- `data/forexfactory_calendar_cache.json`: shared news calendar cache.
- `logs/*.log`: trade, watchdog, and maintenance logs.
- `reports/*`: local maintenance/replay/experiment reports.
- `backups/*`: maintenance backups.

## External Services

- MetaTrader 5 terminal and broker/demo server.
- ForexFactory/FairEconomy calendar JSON for high-impact news.
- Telegram Bot API if `MT5_TELEGRAM_TOKEN` and `MT5_TELEGRAM_CHAT_ID` are set.
- GitHub remote for source control when Jean approves push.

## Security And Safety Boundaries

- Never print or commit `.env` secrets.
- Never place, close, or modify real trades without Jean's explicit approval.
- Demo order permission is explicit; config `execution.trade_enabled` remains
  false by default.
- The current autonomous agent uses `max_parallel_bots: 1`.
- `floor_equity` is the hard equity kill switch.
- News filter defaults to fail-closed on missing calendar data.
- Process guard expects 2 process rows per legitimate Windows/uv trade loop and
  1 on non-Windows unless overridden.

## Operational Notes

- Preferred status checks:
  - `MT5_AGENT.bat preflight`
  - `MT5_AGENT.bat process-guard`
  - inspect latest `data/watchdog_health.jsonl`
  - inspect recent `logs/trade_*_YYYYMMDD.log`
- Warnings can be transient while the runner rotates one symbol at a time; a
  stale journal for a symbol is not automatically fatal if another symbol is
  currently active and the next rotation refreshes it.
- Commit/push code changes only after tests and Jean approval for push.

## Open Questions

- Which legacy BAT files should be deleted after Jean confirms the official
  launcher covers the workflows he still uses?
- Should `MT5_NEWS_FAIL_MODE=open` ever be allowed in demo forward tests, or
  should all serious forward tests remain fail-closed?
- Which research configs with `baseline_equity: 102000.0` should be normalized
  to the current 3000 demo account, archived, or deleted?
