# Autonomous Trade Learning Loop

## 2026-07-01T03:52:55.862964+00:00

Report: `reports\autonomous_trade_reviews\review_20260701_035255.md`

- USDCHF SELL ticket=9017159463 pnl=0.40 causes=profitable_exit action=record_only
- USDCHF SELL ticket=9017931906 pnl=1.42 causes=closed_by_tp action=record_only
- USDCHF BUY ticket=9027605545 pnl=-9.32 causes=closed_by_sl,stop_too_tight action=review_sl_floor_or_position_sizing

## 2026-07-01T04:06:00+00:00

Jean clarified the loop rule: after each useful lesson, apply the improvement to the agent and relaunch it when there are no open positions or pending orders. If a position is open, leave the update staged and report that it is waiting for a clean runtime window. Review reports must include projected loss and projected gain when available from the journal.

## 2026-07-01T04:00:00+00:00

Jean formalized the operating loop: after every closed demo trade, review why
it won or lost, learn only when there is enough evidence, and improve the agent
instead of repeating the same mistake.

Required evidence per trade:

- broker exit evidence: SL, TP, close price, broker comment;
- projected loss to SL;
- projected gain to TP;
- MFE/MAE and whether profit was given back;
- lesson and suggested action, without overfitting one trade.

Implementation follow-up:

- trade execution logs now include projected gain as well as projected loss;
- trade journal context now stores `projected_gain_usd`,
  `projected_loss_usd`, `projected_allowed_loss_usd`, and
  `projected_cash_rr`;
- autonomous trade review reports now try to include projected SL/TP cash and
  projected cash R:R when the journal row is available.
- Windows Task Scheduler job `MT5AgentTradeReview15Min` runs the review script
  every 15 minutes while the PC/session is available:
  `uv run python scripts\autonomous_trade_review.py --limit 50`.

## 2026-07-01T04:12:00+00:00

Deep system review found no active MT5/trading blocker: watchdog, runner, trade
process, preflight, process guard, and MT5 permissions were healthy. Historical
MT5 authorization/IPC errors around 20:10-20:15 were not active in the current
log tail.

One real orchestration risk was fixed: OpenClaw cron and Windows Task Scheduler
can both invoke the autonomous trade review. The review script now uses an
atomic lock beside the state file and exits cleanly with `skipped=lock_active`
when another review is already running, preventing duplicate reports or state
file races.
## 2026-07-01T05:45:02.065627+00:00

Report: `reports\autonomous_trade_reviews\review_20260701_054502.md`

- XAUUSD SELL ticket=9029248068 pnl=3.26 causes=profitable_exit action=record_only

## 2026-07-01T11:02:00+00:00

Jean asked to investigate additional markets so the autonomous demo agent has
fewer dead windows with no trade opportunity. The review found that the active
runner was spending up to 300 seconds on each symbol; adding markets without
shortening that window would make missed M5 crossovers worse.

Changes applied:

- Added safe demo configs for `AUDUSD`, `USDJPY`, `NZDUSD`, and `XAGUSD`.
- Reduced autonomous rotation from `max_seconds=300`, `poll_seconds=10` to
  `max_seconds=20`, `poll_seconds=5`.
- Active config list now covers 10 markets: USDCHF, AUDUSD, GBPJPY, USDJPY,
  EURUSD, GBPUSD, NZDUSD, USDCAD, XAUUSD, XAGUSD.
- Fixed an ADX zero-denominator dtype crash found while scanning XAGUSD.

Validation:

- `uv run pytest -q`: 99 passed.
- `python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml preflight`: OK for 10 configs.
- `uv run python -m mt5_bot.process_guard`: OK, no duplicate trade configs.
- MT5 direct check: connected, trading allowed, positions=0, orders=0.
- Watchdog relaunched at 2026-07-01 10:57 UTC and confirmed using
  `--max-seconds 20 --poll-seconds 5`.
- New SQLite journals were created for AUDUSD, USDJPY, NZDUSD, and XAGUSD.

Risk notes:

- USDCNH and USDSEK were not added because they are exotic/spread-risk markets.
- No manual trade was opened, closed, or modified.

## 2026-07-01T12:00:02.300423+00:00

Report: `reports\autonomous_trade_reviews\review_20260701_120002.md`

- EURUSD SELL ticket=9036796874 pnl=1.70 causes=profitable_exit action=record_only
- EURUSD SELL ticket=9036894446 pnl=0.88 causes=profitable_exit action=record_only
- USDCAD BUY ticket=9036937977 pnl=0.44 causes=profitable_exit action=record_only

## 2026-07-01T12:15:02.268306+00:00

Report: `reports\autonomous_trade_reviews\review_20260701_121502.md`

- USDCAD BUY ticket=9037036946 pnl=0.35 causes=profitable_exit action=record_only
- USDCAD BUY ticket=9037174791 pnl=0.24 causes=profitable_exit action=record_only
- USDCAD BUY ticket=9037294105 pnl=0.37 causes=profitable_exit action=record_only
- USDCAD BUY ticket=9037400286 pnl=0.29 causes=profitable_exit action=record_only

## 2026-07-01T12:30:02.287115+00:00

Report: `reports\autonomous_trade_reviews\review_20260701_123002.md`

- USDCAD BUY ticket=9037444981 pnl=0.14 causes=profitable_exit action=record_only

## 2026-07-01T13:45:02.292806+00:00

Report: `reports\autonomous_trade_reviews\review_20260701_134502.md`

- NZDUSD BUY ticket=9040485569 pnl=2.70 causes=profitable_exit action=record_only

## 2026-07-01T14:00:02.299184+00:00

Report: `reports\autonomous_trade_reviews\review_20260701_140002.md`

- NZDUSD BUY ticket=9040801804 pnl=3.72 causes=profitable_exit action=record_only
- GBPJPY BUY ticket=9040914441 pnl=0.18 causes=profitable_exit action=record_only
- NZDUSD BUY ticket=9040970397 pnl=3.70 causes=profitable_exit action=record_only

## 2026-07-01T15:45:00+00:00

Jean clarified the desired operating model: exposure should expand only when
the market provides valid gates, and contract when conditions are poor. The
previous active profile could rotate through 10 markets but was still capped
to 3 simultaneous portfolio positions.

Change staged/applied to the active 10 demo configs:

- `max_portfolio_open_positions`: 3 -> 10.
- `max_same_currency_positions`: 2 -> 6.
- `max_same_direction_theme_positions`: 1 -> 3.
- `max_total_margin_pct`: 85 -> 35.

Interpretation:

- Current practical simultaneous cap is 10, because the active agent has 10
  markets and V1 allows one position per symbol/magic.
- Bad markets still result in zero entries because the signal, spread, news,
  ADX/ATR, SL/spread, loss caps, setup memory, and equity guards still apply.
- Reaching 15 simultaneous positions would require either more safe markets or
  pyramiding/multiple entries per symbol, which needs a separate aggregate open
  risk cap before enabling.

Validation:

- `uv run pytest -q`: 99 passed.
- Agent preflight: OK for 10 configs.
- `uv run python -m mt5_bot.process_guard`: OK.
- MT5 direct check showed one open EURUSD SELL position, no pending orders; no
  restart was performed.

## 2026-07-01T15:55:00+00:00

Jean clarified an operating rule for the expanded multi-market agent:
increasing the number of possible open trades must not make the agent neglect
live positions.

Rule:

- Live positions have priority over searching for fresh entries.
- Broker SL/TP remains the first hard protection layer.
- Agent-side dynamic management (telemetry, time stop, profit-lock, trailing,
  partial close) must be checked as soon as practical for symbols with open
  positions.
- Do not restart the watchdog just to activate this while a position is open;
  stage and validate the change, then activate on a clean window unless Jean
  explicitly approves the operational risk.

Implementation staged:

- Added live-position-first config ordering to `agent_runner`.
- Added explicit `prioritize_live_positions: true` to the active autonomous
  config.
- Added tests for the live-position prioritization behavior.

## 2026-07-01T16:05:00+00:00

Jean asked to keep investigating additional markets for the autonomous agent.
Initial MT5 broker screen used live symbol info, M5/H1 bars, current spread,
ATR, ADX, trade mode, min lot, and margin calculation. No live/demo orders
were opened or modified.

Initial shortlist:

- `EURGBP`: low spread, low margin, strong ADX; no current crossover.
- `EURCAD`: low spread/ATR ratio, low margin, acceptable ADX; no current
  crossover.
- `EURAUD`: very low spread/ATR ratio, low margin, acceptable ADX; no current
  crossover.
- `CHFJPY`: low spread/ATR ratio, low margin, acceptable ADX; no current
  crossover.
- `EURJPY`: watchlist; low cost but ADX was weak at scan time.

Rejected for now:

- `CADCHF` and `GBPCAD` had current EMA triggers, but spread/ATR cost was too
  high for clean activation.
- `US30`, `US30M`, and `UK100` were not full trade-mode candidates for this
  agent profile.
- `XPDUSD` and `XPTUSD` required too much margin for the ~3k demo account.
- `WTI`, `GERN`, `HGER`, `XAUEUR`, and `XAGEUR` had poor spread/ATR economics
  for this M5 bot profile at scan time.

Next gate before activation:

- Re-scan shortlisted symbols across another session.
- If spreads and ADX stay acceptable, add them as controlled demo configs with
  low risk, unique magic numbers, preflight, tests, process guard, and no push
  unless Jean requests it.

## 2026-07-01T16:20:00+00:00

Second market incorporation scan per Jean's request. Expanded review across
liquid non-active FX crosses plus metals/indices/energy. Checks included MT5
trade mode, tick availability, M5/H1 history, min lot, margin, spread/ATR,
current ADX, current signal, and a lightweight recent M5 execution simulation:
EMA 5/13 crossover, H1 trend alignment, RSI, ATR, ADX, ATR SL/TP, 24-bar time
stop, approximate spread cost.

Outcome:

- No new symbol passed activation gates for immediate inclusion.
- `EURAUD`, `EURCAD`, and `EURGBP` passed the first microstructure screen but
  failed the recent execution simulation.
- `AUDJPY` and `GBPCHF` were closest on recent simulation, but failed live
  activation quality (`AUDJPY` weak current ADX / spread edge, `GBPCHF`
  spread/ATR above threshold).
- `CADCHF` and `GBPCAD` previously showed live triggers, but repeated checks
  kept them rejected due spread/ATR cost and poor simulation quality.
- Indices/energy/metals outside XAU/XAG remained unsuitable for this profile
  due trade mode, stale data, coarse lot, margin, or spread/ATR economics.

Decision:

- Do not add new markets now.
- Keep watchlist: `AUDJPY`, `GBPCHF`, `EURGBP`, `EURJPY`.
- Re-scan in a different liquidity window before any config activation.
- Maintain current 10-market rotation and live-position priority.

## 2026-07-01T16:25:00+00:00

Jean clarified the operating boundary for all future requests around this MT5
agent:

- The autonomous agent must keep running without interruption by default.
- Any analysis, investigation, market scan, report, code review, or planning
  Jean asks for is external to the running agent unless Jean explicitly asks to
  change the live runtime.
- Do not stop or restart the agent for normal investigation work.
- Only stop/relaunch the watchdog/runner to activate an implemented update,
  and only after confirming there are no live positions and no pending orders.
- If an update is prepared while a position is live, stage, test, and commit it,
  then wait for a clean MT5 window before relaunching.
- Never manually open, close, or modify trades while doing these external tasks
  unless Jean gives explicit current-conversation approval.

Current confirmation at the time of this note:

- Watchdog active.
- Runner active.
- Trade loop active.
- `process_guard`: OK.
- MT5 connected with trading allowed.
- Open positions: 0.
- Pending orders: 0.

## 2026-07-01T17:15:00+00:00

Jean clarified the next learning focus: winning trades must be reviewed with
the same seriousness as losing trades. The review should answer why the trade
won, how it won, whether it could have won more, and whether higher size would
have been justified.

Evidence from closed positions available at this scan:

- Closed positions reviewed: 8.
- Winners: 7.
- Losers: 1.
- Net realized PnL: +12.66 USD.
- Winners realized about +21.98 USD, while reconstructed full-volume MFE was
  about +54.26 USD. This means there was meaningful upside left on the table,
  mostly from partial exits/profit-lock behavior.
- Main winners with notable unused MFE: `NZDUSD`, `EURUSD`, `XAUUSD`, and
  `USDCAD`.
- The one loss, `USDCHF` BUY, looked strong by static math (bullish trend,
  RSI 61.88, ADX 45.03) but still hit SL. This is evidence against treating
  "certainty" as a static entry feeling.

Operating lesson:

- Do not implement unlimited or emotion-based size increases.
- Prefer evidence-based scaling: only add size or allow higher risk after the
  position proves itself with favorable movement, low MAE, healthy ADX,
  clean spread/ATR, no correlation crowding, and intact account risk caps.
- Future improvement candidate: a confidence/add-on module that can scale
  winners after confirmation, not before confirmation, with aggregate open
  risk limits.

## 2026-07-01T16:00:02.395619+00:00

Report: `reports\autonomous_trade_reviews\review_20260701_160002.md`

- EURUSD SELL ticket=9043963496 pnl=1.53 causes=profitable_exit action=record_only
- EURUSD SELL ticket=9044049629 pnl=0.66 causes=profitable_exit action=record_only

## 2026-07-01T17:25:00+00:00

Winner scaling update staged externally while the live agent kept running.
Jean asked to implement this after the current operation finishes and relaunch
only in a clean MT5 window.

Implementation prepared:

- Added optional winner scaling fields to `BotConfig`.
- Added `TradeExecutor.manage_winner_scaling`.
- Winner scaling is disabled by default and was not enabled in active configs
  while `USDJPY` was live.
- Gate design:
  - only after favorable MFE progress;
  - current profit must remain near MFE, not a deep retrace;
  - MAE must be small relative to MFE;
  - ADX must meet a configurable floor;
  - spread/ATR must stay clean;
  - add-on volume is a fraction of current volume;
  - add-on projected loss to current SL must fit a separate risk cap;
  - one add-on per position ticket, tracked through `runtime_events`;
  - every add-on passes `order_check` before any send.

Validation:

- Focused tests: 21 passed.
- Full suite: 105 passed.
- Agent preflight: OK for 10 configs.
- `process_guard`: OK.
- MT5 still had one live `USDJPY` BUY position, so no relaunch was performed.

Activation rule:

- When MT5 positions=0 and orders=0, enable the feature in selected active
  configs, run tests/preflight/process guard, then relaunch watchdog/runner.

## 2026-07-01T17:29:59+00:00

Jean confirmed the staged winner-scaling lesson should be activated when the
current operation finishes.

Runtime boundary preserved:

- MT5 still had one live `USDJPY` BUY position when checked.
- No trade was opened, closed, or modified manually.
- No watchdog/runner relaunch was performed.

External activation monitor:

- OpenClaw cron job: `a2af3140-c107-4045-bfaa-46559f206a74`
  (`MT5 activate winner scaling when clean`).
- Runs every 5 minutes.
- If any position or pending order exists, it exits silently and leaves the
  live agent untouched.
- If MT5 is clean, it enables conservative winner scaling in active configs,
  runs tests/preflight/process guard, re-checks MT5 is still clean, relaunches
  watchdog/runner, commits locally, reports to Jean, and disables/removes the
  activation job when possible.

