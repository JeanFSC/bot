# MT5 Multi-Agent Implementation Phases - 2026-07-02

Purpose: convert the enterprise multi-agent plan into an implementation
sequence that can be executed safely while the current autonomous demo agent
keeps running.

## Ground Rules

- Existing MT5 agent keeps running by default.
- Normal analysis, code, tests, reports, and scans are external to the live
  agent.
- No manual trade open/close/modify without Jean's current approval.
- Runtime relaunches happen only when MT5 is clean: positions=0 and orders=0.
- New processes that can modify trades must start in report-only mode first,
  then graduate after tests and a clean runtime activation window.

## Agent/Process Map

### 1. Entry Agent

Current implementation: `mt5_bot.agent_runner` + `mt5_bot trade` rotation.

Role:

- Scan symbols.
- Generate entries.
- Open positions only when gates pass.

Near-term changes:

- Keep it as the entry scanner.
- Reduce responsibility for live-position management as the supervisor matures.

### 2. Live Position Supervisor

Implementation started in this phase:

- Module: `src/mt5_bot/live_position_supervisor.py`
- Launcher:
  - `MT5_AGENT.bat supervisor-once`
  - `MT5_AGENT.bat supervisor-bg`

Role:

- Monitor open positions across all active configs.
- Never search for new entries.
- Map MT5 positions to owning config by `(symbol, magic)`.
- Run deterministic management rules:
  - position telemetry/MFE/MAE,
  - missing SL/TP alert,
  - early no-favorable-excursion exit,
  - time stop,
  - winner scaling,
  - profit lock,
  - partial close,
  - trailing stop.

Current safety state:

- Implemented and tested.
- `supervisor-once` and `supervisor-bg` are report-only.
- `supervisor-demo-bg` exists as the explicit action-enabled launcher, but was
  not started in this phase.
- Action-enabled supervisor should be activated only after another validation
  pass and clean-window decision.

### 3. Portfolio Risk Agent

Next implementation phase.

Role:

- Compute account heat from real broker projections.
- Estimate total cash loss if every active SL hits.
- Track exposure by currency, metal, direction, and correlated theme.
- Emit allow/reduce/block decisions to the Entry Agent.

Initial mode:

- Report-only.
- No blocking until its calculations are validated against live MT5 state.

### 4. Learning Agent

Current implementation:

- `scripts/autonomous_trade_review.py`
- `agent_runner.learn_from_closed_deals`
- `docs/memory/autonomous-trade-learning-loop.md`

Next changes:

- Separate winner review and loser review into structured outputs.
- Store MFE/MAE capture ratio and "could have scaled" verdict.
- Produce update proposals instead of ad hoc lessons.

### 5. Infra / Watchdog Agent

Current implementation:

- `mt5_bot.agent_watchdog`
- `mt5_bot.process_guard`
- OpenClaw cron for reviews.

Next changes:

- Deterministic local checks should not depend on LLM tokens.
- Alert if watchdog, runner, supervisor, or MT5 permissions degrade.
- Track Codex account/provider fallback status separately from trading health.

### 6. Market Research Agent

Current implementation:

- Manual scans and reports.

Next changes:

- Scheduled candidate scan in report-only mode.
- Candidate score must include trade mode, spread/ATR, ADX, margin, lot size,
  recent strategy simulation, and correlation with active book.

### 7. Reporting / Dashboard Agent

Next phase after supervisor + portfolio heat.

Role:

- Give Jean one control-room snapshot:
  - active processes,
  - live positions,
  - SL/TP integrity,
  - open risk to SL,
  - floating PnL,
  - daily closed PnL,
  - supervisor last-managed timestamps,
  - pending update queue,
  - cron/provider fallback health.

## Phase Order

### Phase 1 - Live Position Supervisor Foundation

Status: completed for report-only foundation after council review fixes.

Deliverables:

- `live_position_supervisor` module.
- Report-only CLI.
- `MT5_AGENT.bat` commands.
- Unit tests.
- One live report-only run.

Exit gate:

- Tests pass.
- Preflight remains OK.
- process_guard OK.
- Report-only run sees live positions without opening/closing/modifying trades.

Completion evidence:

- External council review found three blockers before close: report-only still
  touched MT5 trade-validation APIs, duplicate supervisor processes were not
  guarded, and duplicate `(symbol, magic)` config ownership could silently
  overwrite.
- Fixes applied:
  - report-only supervisor now records missing SL/TP alerts and MFE/MAE
    telemetry only;
  - action management paths require explicit `--allow-demo-actions`;
  - duplicate `(symbol, magic)` owner configs fail fast;
  - process guard now detects duplicate `live_position_supervisor`
    continuous services.
- Focused tests: `16 passed` for supervisor/process guard/portfolio heat.
- Preflight: `AGENT_PREFLIGHT_OK configs=10`.
- process_guard: OK, no duplicate trade configs and no duplicate supervisors.
- Live report-only run against MT5 saw 3 owned positions, 0 unknown positions,
  and emitted telemetry only:
  - `USDJPY` ticket `9386448297`;
  - `AUDUSD` ticket `9388530132`;
  - `USDCAD` ticket `9388560542`.
- Continuous report-only supervisor is running through `MT5_AGENT.bat
  supervisor-bg`, writing `data/live_position_supervisor.jsonl` every 5
  seconds.
- It is not action-enabled. `supervisor-demo-bg` exists for later controlled
  activation, but was not started.
- Windows/uv singleton process chains show as 3 process rows; process_guard now
  treats one 3-row chain as normal and flags duplicated singleton chains.

### Phase 2 - Supervisor Controlled Activation

Status: not activated.

Deliverables:

- Add explicit `supervisor-demo-bg` or service task with action permission.
- Start only after clean-window validation or explicit Jean approval.
- Log every supervisor action to JSONL and SQLite runtime events.

Exit gate:

- Supervisor can run beside Entry Agent without duplicate entry processes.
- No action without matching `(symbol, magic)` config.
- No missing SL/TP goes unreported.

### Phase 3 - Portfolio Heat Engine

Status: report-only foundation implemented.

Deliverables:

- Cash risk-to-SL report for all open positions.
- Currency/theme exposure report.
- Report-only block/reduce recommendations.

Exit gate:

- Calculations match MT5 `order_calc_profit`.
- No false high-risk/low-risk classification on test fixtures.

Current evidence:

- Module: `src/mt5_bot/portfolio_heat.py`.
- Launcher:
  - `MT5_AGENT.bat heat-once`;
  - `MT5_AGENT.bat heat-bg`.
- Tests cover risk-to-SL projection, unprotected-position blocking, and crowded
  currency reduction.
- Live MT5 report-only run:
  - checked positions: 3;
  - owned positions: 3;
  - unknown positions: 0;
  - equity range observed during validation: `3003.56` to `3006.27`;
  - margin usage: about `8.79%`;
  - floating PnL range observed: `-1.54` to `+1.17`;
  - total risk to SL: `11.20 USD` / `0.37%`;
  - total reward to TP: `22.38 USD`;
  - decision: `allow_new_entries`;
  - unprotected positions: 0.
- Continuous report-only heat monitor is running through `MT5_AGENT.bat
  heat-bg`, writing `data/portfolio_heat.jsonl` every 15 seconds.
- Heat monitor has no order-send or order-modify path; it reads account and
  positions and uses MT5 `order_calc_profit` for risk/reward projection.
- Duplicate `(symbol, magic)` ownership now fails fast here too.

### Phase 4 - Entry Agent Integration

Deliverables:

- Entry Agent consumes Portfolio Risk Agent decision.
- Blocks/reduces new entries when portfolio heat is too high.
- Supervisor remains responsible for live positions.

Exit gate:

- New entry decisions include portfolio heat context in journal.
- Existing live positions continue to be managed.

### Phase 5 - Learning Agent Upgrade

Status: implemented for structured winner diagnostics.

Deliverables:

- Structured post-trade review for:
  - why winner won,
  - whether it could scale,
  - MFE capture,
  - MAE stress,
  - loss root cause,
  - symbol-specific changes.

Exit gate:

- Lessons produce specific pending updates with tests.
- Updates activate only through clean-window gate.

Current evidence:

- Script upgraded: `scripts/autonomous_trade_review.py`.
- Winner diagnostics now include:
  - MFE capture ratio;
  - winner quality (`clean_winner`, `winner_left_money_on_table`,
    `survived_winner`, etc.);
  - scale verdict (`scale_candidate_clean_winner`,
    `no_scale_survived_winner`, etc.).
- Tests added for clean scale candidate vs survived winner.
- Live review generated `reports/autonomous_trade_reviews/review_20260702_031400.md`.
- Two new winners were classified as left-money-on-table scale candidates:
  - `AUDUSD SELL` ticket `9052018329`, PnL `+1.62`, MFE capture `0.305`;
  - `USDCAD BUY` ticket `9052024633`, PnL `+0.41`, MFE capture `0.277`.
- Suggested action from both: `review_winner_runner_or_scale_logic`.

### Phase 6 - Control Room

Status: implemented as read-only snapshot.

Deliverables:

- Local dashboard/report artifact.
- Telegram status summary.
- Alerts for critical conditions.

Exit gate:

- Jean can ask "como va el agente" and get a single reliable operational
  snapshot.

Current evidence:

- Module: `src/mt5_bot/control_room.py`.
- Launcher: `MT5_AGENT.bat control-room`.
- Reads latest supervisor, portfolio heat, watchdog, and process_guard state.
- Does not connect to MT5 directly and has no trade-action path.
- Tests included in full suite.
- Live command output validated:
  - `CONTROL_ROOM OK`;
  - process_guard OK;
  - positions `3/3`;
  - unknown positions `0`;
  - unprotected positions `0`;
  - risk to SL `11.20 USD`;
  - heat decision `allow_new_entries`;
  - supervisor managed positions `3`.

## Current Recommendation

Do not jump directly to many independent action-enabled agents. The robust path
is:

1. Build deterministic supervisor.
2. Run it report-only.
3. Validate against live MT5 state.
4. Activate it only when the operating rule allows.
5. Add Portfolio Heat next.

This avoids the main failure mode of multi-agent trading systems: multiple
processes acting on the same account without one shared risk truth.
