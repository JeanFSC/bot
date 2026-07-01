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
