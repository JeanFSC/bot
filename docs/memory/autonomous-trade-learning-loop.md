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

