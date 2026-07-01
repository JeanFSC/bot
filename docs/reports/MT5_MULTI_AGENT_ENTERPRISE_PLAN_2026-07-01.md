# MT5 Autonomous Trading System - Enterprise Multi-Agent Upgrade Plan

Generated: 2026-07-01

Purpose: provide a serious architecture and execution plan for upgrading the
current MT5 autonomous demo trading system into a more robust multi-agent /
multi-process trading platform. This document is written so Jean can ask
Claude or another reviewer for a second opinion.

## Executive Summary

The project has moved from a single-symbol/small-rotation bot toward a
continuous autonomous demo agent:

- The active agent runs through `MT5_AGENT.bat watchdog-bg`.
- `agent_watchdog` supervises `agent_runner`.
- `agent_runner` rotates the active configs in `config/autonomous_agent.yaml`.
- Current active universe: 10 markets.
- Rotation speed: `max_seconds: 20`, `poll_seconds: 5`.
- Live-position priority is enabled: `prioritize_live_positions: true`.
- Portfolio capacity was raised from 3 to 10 practical simultaneous positions.
- Winner scaling has been implemented and enabled in the 10 active configs.
- The learning loop reviews closed trades and records lessons.
- OpenClaw cron now has two OpenAI/Codex OAuth profiles in fallback order and
  model fallbacks for the overnight learning loop.

The strongest next improvement is not simply "more markets" or "more size".
The strongest next improvement is to split the system into specialized
deterministic agents/processes:

1. Entry Agent.
2. Live Position Supervisor.
3. Portfolio Risk Agent.
4. Learning Agent.
5. Infrastructure / Watchdog Agent.
6. Market Research Agent.
7. Reporting / Dashboard Agent.

The most urgent upgrade is a dedicated Live Position Supervisor. Today the
agent manages positions by symbol rotation. That works, but it is not strong
enough for a future state with 5, 10, or 15 open positions. The broker SL/TP is
the hard protection, but dynamic management should not wait for the entry
scanner to rotate through each symbol.

## Current State

### Active Runtime

- Launcher: `MT5_AGENT.bat watchdog-bg`.
- Watchdog: `mt5_bot.agent_watchdog`.
- Runner: `mt5_bot.agent_runner`.
- Trade loop: `mt5_bot trade --config ...`.
- Active agent config: `config/autonomous_agent.yaml`.
- `max_parallel_bots: 1`.
- `max_seconds: 20`.
- `poll_seconds: 5`.
- `prioritize_live_positions: true`.
- `floor_equity: 2900.0`.
- `allow_demo_orders: true`.

### Active Market Universe

From `config/autonomous_agent.yaml`:

- `USDCHF`
- `AUDUSD`
- `GBPJPY`
- `USDJPY`
- `EURUSD`
- `GBPUSD`
- `NZDUSD`
- `USDCAD`
- `XAUUSD`
- `XAGUSD`

### Current Guardrails

Across active configs:

- `max_portfolio_open_positions: 10`
- `max_same_currency_positions: 6`
- `max_same_direction_theme_positions: 3`
- `max_total_margin_pct: 35.0`
- `winner_scaling_enabled: true`
- `winner_scaling_max_addon_risk_pct: 0.10`

### Recent Evidence

Latest maintenance snapshot seen during this planning cycle:

- Closed trades: 34.
- Wins / losses: 33 / 1.
- Win rate: 97.06%.
- Net realized PnL: +21.97 USD.
- Recent loss: USDCHF -9.32 USD.
- Recent winner-review lesson: winners left meaningful MFE on the table.

Important interpretation:

- The high win rate is promising but still a small sample.
- The USDCHF loss shows that "strong-looking" static math can still fail.
- The winner review shows upside was left on the table, but the correct answer
  is evidence-based scaling after confirmation, not unlimited size at entry.

## Core Operating Principles

1. Protect capital first.
2. Never manually open, close, or modify trades without explicit current
   approval from Jean.
3. Keep the live agent running by default.
4. Treat analysis, reports, scans, and implementation work as external to the
   live agent.
5. Only relaunch the trading runtime to activate an update after confirming:
   positions=0 and pending orders=0.
6. If positions are live, prepare/test/commit updates, but wait for a clean
   MT5 window before activation.
7. More trades are acceptable only when market evidence and portfolio heat allow
   them.
8. Winner scaling should be based on confirmation, MFE, MAE, ADX, spread/ATR,
   and aggregate risk, not on emotional certainty.
9. Critical live-trade management should be deterministic, local, and fast.
10. LLMs should analyze, audit, explain, learn, and propose changes; they
    should not be the only real-time safety layer.

## Proposed Enterprise Architecture

### 1. Entry Agent

Responsibility:

- Search for trade entries.
- Rotate or schedule market scans.
- Evaluate signal quality.
- Open a new position only after all gates pass.

Owns:

- Signal generation.
- Session filters.
- News filters.
- Spread filters.
- Setup confidence.
- Entry order check/send.

Must not own:

- Continuous management of already-open positions.
- Global portfolio heat.
- Post-trade code updates.

Inputs:

- Market data from MT5.
- Config per symbol.
- Portfolio Risk Agent allow/block/reduce decision.
- Market Research Agent active universe list.

Outputs:

- Entry decision.
- Order request.
- Journal row.
- Runtime event.

### 2. Live Position Supervisor

This is the highest-priority new component.

Responsibility:

- Monitor all open positions continuously, independent of entry scanning.
- Run every few seconds.
- Ensure every position has valid broker-side SL/TP.
- Apply dynamic management rules.

Functions:

- SL/TP integrity check.
- Missing SL/TP emergency alert.
- Profit-lock management.
- Trailing stop management.
- Time stop.
- Partial close when configured.
- Winner scaling after confirmation.
- Drawdown response.
- "Last managed at" tracking per ticket.
- Position-level audit logs.

Why it matters:

- The current system manages dynamically by symbol rotation.
- With 4+ positions, rotation is acceptable but not enterprise-grade.
- With 10+ positions, a dedicated supervisor becomes necessary.

Design:

- Deterministic Python process, not LLM-heavy.
- Reads all `positions_get()` on every cycle.
- Maps tickets to owning config/magic/symbol.
- Applies only safe deterministic actions.
- Writes to `runtime_events` and a supervisor heartbeat file.
- Refuses to act if MT5 trade permissions are disabled.

Safety:

- No new entries.
- No discretionary closes unless rule-based and tested.
- Every modification must be recorded with old/new SL/TP and reason.
- If uncertain, alert and do nothing.

### 3. Portfolio Risk Agent

Responsibility:

- Decide if the whole account can accept more risk.
- Compute account heat in real money, not only number of trades.

Functions:

- Projected loss if all active SLs are hit.
- Projected gain if all TPs are hit.
- Open risk as % of equity.
- Margin used and free margin.
- Exposure by currency.
- Exposure by direction and theme.
- Correlation / same macro thesis detection.
- Drawdown from recent balance/equity high.
- Daily and weekly loss circuit breakers.
- New-entry allow/block/reduce decision.

Why it matters:

- The project now allows up to 10 positions.
- Ten small trades can still be one correlated thesis.
- Current guardrails help, but a dedicated risk agent should know the whole
  account state before any entry/add-on.

Example:

- `NZDUSD SELL` and `AUDUSD SELL` can be correlated commodity/high-beta USD
  exposure.
- `USDJPY BUY` and `GBPJPY BUY` add JPY short exposure.
- The risk engine should see that before allowing more similar trades.

### 4. Learning Agent

Responsibility:

- Review closed trades.
- Learn from both winners and losers.
- Propose changes only when evidence is strong.

Functions:

- Loss postmortem.
- Winner postmortem.
- MFE/MAE reconstruction.
- Exit quality analysis.
- SL/TP quality analysis.
- Spread/slippage/retcode analysis.
- Winner scaling "would it have helped?" simulation.
- Symbol-level performance report.
- Config-change proposal.
- Pending-update generation.

Important:

- The Learning Agent can be LLM-assisted.
- It should not directly relaunch live trading while positions are open.
- It should output a patch proposal or pending update, then use the update gate.

### 5. Infrastructure / Watchdog Agent

Responsibility:

- Keep the trading system alive and safe.
- Monitor runtime health, not market opportunity.

Functions:

- Watchdog status.
- Runner status.
- Process guard.
- Duplicate process detection.
- MT5 connection status.
- Account permissions.
- Journal freshness.
- Cron status.
- Token/provider fallback status.
- Log error scanning.
- Clean-window relaunch gate.
- Notification delivery health.

Important:

- This should be mostly deterministic.
- It should not rely fully on Codex tokens for basic checks.
- If LLM/token systems fail, basic health checks should still run locally.

### 6. Market Research Agent

Responsibility:

- Search for new markets without polluting the live agent.
- Keep candidates in watchlist until evidence passes.

Functions:

- MT5 symbol availability.
- Trade mode.
- Data quality M5/H1.
- Spread/ATR.
- ADX and trend strength.
- Margin/min lot.
- Replay/backtest sample.
- Current gate scan.
- Reject/Watchlist/Activate recommendation.

Recent watchlist:

- `AUDJPY`: closest candidate, but not activated.
- `GBPCHF`: watchlist, cost/ADX concerns.
- `EURGBP`: cost good, recent simulation negative.
- `EURJPY`: secondary watchlist.

Rejected examples:

- `CADCHF`, `GBPCAD`: live triggers seen, but spread/ATR and simulation quality
  did not justify activation.
- Some indices/energy/exotics: rejected due trade mode, data, lot size, margin,
  or spread/ATR economics.

### 7. Reporting / Dashboard Agent

Responsibility:

- Provide a clear control-room view.
- Make Jean and the operators aware of risk without manually inspecting logs.

Dashboard should show:

- Watchdog/runner/trade loop state.
- Current symbol being processed.
- Open positions with ticket, side, volume, SL, TP, PnL.
- Projected loss to SL.
- Projected gain to TP.
- Account heat.
- Margin and margin level.
- Last management timestamp per ticket.
- Winner scaling attempts.
- Profit-lock/trailing actions.
- Cron status.
- Token/provider fallback status.
- Recent closed trades and review actions.

## Ten Enterprise Improvements

### 1. Dedicated Live Position Supervisor

Build a new process responsible only for live positions. It should inspect all
positions every few seconds and manage protection dynamically. This is the most
important change because scaling to 10+ positions makes rotation-based dynamic
management weaker.

Acceptance criteria:

- Supervisor starts/stops under watchdog.
- Reads all open positions.
- Records heartbeat.
- Records `last_managed_at` per ticket.
- Detects missing SL/TP.
- Runs profit-lock/trailing/time-stop/winner-scaling logic.
- Has focused tests.
- Does not open new entries.

### 2. Portfolio Heat Engine

Build account-level risk math independent of each symbol loop.

Acceptance criteria:

- Computes total projected loss to SL.
- Computes total projected gain to TP.
- Computes open risk % equity.
- Computes margin usage.
- Computes exposure by currency and direction.
- Returns allow/block/reduce decision for new entries and add-ons.

### 3. Multi-Agent Runtime Split

Separate the current single rotating agent into specialized processes:

- Entry Agent.
- Live Position Supervisor.
- Portfolio Risk Agent.
- Learning Agent.
- Infrastructure Agent.
- Market Research Agent.
- Reporting Agent.

Phase this gradually. Do not create all at once.

### 4. Post-Trade Review 2.0

Upgrade trade review so every closed trade has:

- Entry thesis.
- Exit reason.
- MFE.
- MAE.
- SL/TP quality.
- Spread at entry.
- Slippage.
- Time in trade.
- Whether winner scaling would have helped.
- Whether risk should have been reduced or increased.

Acceptance criteria:

- Closed-trade report includes MFE/MAE.
- Winner and loser reviews are symmetrical.
- Lessons are tagged as `record_only`, `config_update`, `code_update`, or
  `research_needed`.

### 5. Pending Update Gate

Formalize the existing manual discipline:

- Prepare update.
- Test update.
- Commit update.
- Wait for positions=0 and pending orders=0.
- Relaunch only then.

Acceptance criteria:

- `data/pending_update.json` or equivalent exists.
- Contains commit hash, validation status, activation command, and clean-window
  requirements.
- Activation script refuses to run when positions or orders exist.

### 6. Deterministic Cron Layer

Do not depend on LLM/Codex for basic monitoring.

Acceptance criteria:

- Local scheduled task can check MT5, process guard, closed trades, and logs.
- If tokens are exhausted, basic health and trade-review data collection still
  runs.
- LLM is only used for interpretation or code proposal.

### 7. Execution Quality Analytics

Store and analyze broker execution quality:

- Spread at entry.
- Spread at exit if available.
- Slippage vs requested price.
- Retcode.
- Fill policy.
- Requotes/rejections.
- Time to fill.
- Symbol-specific execution quality.

Use this to remove symbols that look good in signals but lose edge in execution.

### 8. Market Universe Governance

Make market activation a formal pipeline:

1. Candidate scan.
2. Watchlist.
3. Replay/backtest.
4. Demo shadow mode.
5. Small-size activation.
6. Full active universe.

Acceptance criteria:

- No symbol is activated only because it has a current trigger.
- Each candidate has a written reason for accept/reject/watchlist.
- Spread/ATR and margin are mandatory gates.

### 9. Defensive Mode / Circuit Breakers

The system needs automatic degradation modes.

Triggers:

- Floating drawdown above threshold.
- Projected SL loss above threshold.
- Margin usage above threshold.
- Too many correlated trades.
- Repeated losses in same symbol/theme.
- MT5 connectivity instability.

Actions:

- Block new entries.
- Allow only position management.
- Reduce add-ons.
- Tighten entry filters.
- Require stronger ADX/spread/ATR.
- Alert Jean.

### 10. Control-Room Dashboard

Create a text/HTML dashboard with:

- Current positions.
- Account risk.
- Agent status.
- Cron status.
- Recent trades.
- Open update queue.
- Token/account fallback state.

This can start as a Markdown/JSON report and later become a small local web UI.

## Proposed Implementation Roadmap

### Phase 0 - Keep Runtime Safe

Do now / always:

- Do not interrupt live agent for planning.
- Do not relaunch while positions are open.
- Keep commits local unless Jean asks for push.
- Maintain `process_guard` checks.

### Phase 1 - Live Position Supervisor

Scope:

- Add `mt5_bot.live_position_supervisor`.
- Add supervisor config section.
- Add command: `MT5_AGENT.bat supervisor` or integrated watchdog child.
- Reuse existing executor management logic where possible.
- Write tests around missing SL/TP, trailing/profit-lock decision, and no-entry
  guarantee.

Activation:

- Build and test externally.
- If positions are live, stage only.
- Activate only in clean MT5 window.

### Phase 2 - Portfolio Heat Engine

Scope:

- Add `mt5_bot.portfolio_heat`.
- Compute projected SL/TP money using MT5 `order_calc_profit` where possible.
- Expose a function for Entry Agent and Live Position Supervisor.
- Add report output.

Activation:

- First report-only mode.
- Then block/reduce mode after validation.

### Phase 3 - Dashboard / Control Report

Scope:

- Generate `reports/live_control_room.md` and JSON equivalent.
- Include open positions, risk, projected SL/TP, last management time, process
  state, cron state, and pending update state.

Activation:

- Deterministic script.
- Can run from Windows Task Scheduler.
- Telegram alert only on status changes or risks.

### Phase 4 - Learning Agent 2.0

Scope:

- Upgrade closed-trade review to include MFE/MAE, missed upside, winner scaling
  opportunity, execution cost, and symbol-level lessons.
- Make each recommendation produce a structured patch proposal.

Activation:

- Report-only first.
- Code/config changes go through pending update gate.

### Phase 5 - Market Research Agent

Scope:

- Formal candidate pipeline.
- Watchlist with time-window rescans.
- Reject/activate evidence packs.

Activation:

- Add markets only after repeated evidence.

## Suggested First Build

Start with:

1. Live Position Supervisor.
2. Portfolio Heat Engine in report-only mode.
3. Live control-room report.

Reason:

- These reduce operational risk immediately.
- They make scaling to more trades safer.
- They do not require new market assumptions.
- They are mostly deterministic and do not depend on LLM tokens.

## Risks And Warnings

### Over-agentization

Too many agents too quickly can create coordination bugs. The first split
should be simple:

- Entry Agent keeps entries.
- Live Position Supervisor owns open-position management.

Only after that should the Portfolio Risk Agent become an active blocker.

### Conflicting Control

If multiple processes can modify SL/TP, they can fight each other. There must
be ownership rules:

- Live Position Supervisor owns modifications to open positions.
- Entry Agent owns entries only.
- Portfolio Risk Agent owns allow/block/reduce decisions.
- Learning Agent owns proposals, not live execution.

### Token Dependency

Critical checks must not depend on Codex/OpenClaw tokens. LLMs are useful for
analysis, not as the only safety rail.

### Sample Size

The current results are promising but small. The system should not increase
aggression only because of a short win streak.

### Winner Scaling Risk

Winner scaling can improve upside, but it can also add risk at the worst time
if it fires late or during a retrace. It must remain capped and measured.

## Claude Review Brief

Please review this MT5 autonomous trading system upgrade plan as an external
architecture/risk reviewer.

Focus on:

1. Whether splitting into Entry Agent, Live Position Supervisor, Portfolio Risk
   Agent, Learning Agent, Infrastructure Agent, Market Research Agent, and
   Dashboard Agent is the right architecture.
2. Whether the first implementation should be the Live Position Supervisor.
3. Whether position management should be centralized in a deterministic process
   rather than handled by the rotating entry loop.
4. Whether the proposed Portfolio Heat Engine covers enough risk dimensions.
5. Whether winner scaling is appropriately constrained.
6. Whether the pending-update/clean-window activation gate is sufficient.
7. What failure modes are missing.
8. What should be done before allowing 10+ simultaneous positions.
9. What parts should never depend on LLM tokens.
10. What should be simplified before implementation.

Important context:

- This is a demo MT5 account around 3000 USD equity.
- The current bot already has broker-side SL/TP.
- The current bot rotates 10 markets with live-position priority.
- Winner scaling is active but should remain conservative.
- User wants aggressive growth, but risk controls must remain explicit.
- No live trade should be manually opened, closed, or modified by an assistant
  without explicit current approval.

## Recommended Verdict

Proceed, but in this order:

1. Build Live Position Supervisor.
2. Build Portfolio Heat Engine in report-only mode.
3. Build control-room dashboard/report.
4. Upgrade post-trade review.
5. Formalize pending-update activation.
6. Only then consider more markets, more position count, or more aggressive
   winner scaling.

Do not implement the full multi-agent system in one jump. The correct
enterprise path is staged, measurable, and reversible.
