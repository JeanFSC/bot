# MT5 Additional Trade Review - 2026-07-02

Generated from MT5 history, local autonomous review reports, SQLite/log
inspection, and M1/M5 bar reconstruction.

Scope: additional closed autonomous demo trades after the earlier winner/loss
review block. This review groups MT5 deals by real `position_id`, so partial
closes and SL moves are evaluated as one position when appropriate.

## Summary

Window reviewed: `2026-07-01T17:00:00+00:00` to
`2026-07-02T13:20:59+00:00`.

- Closed positions reviewed: 12.
- Winners: 10.
- Losers: 2.
- Gross wins: +12.70 USD.
- Gross losses: -15.18 USD.
- Net PnL: -2.48 USD.

Core finding:

- The system kept a high win rate, but average win size was too small relative
  to the two losses. This is the same structural problem Jean pointed out:
  winners are being protected quickly, but losses can still erase many small
  wins.

## Symbol Summary

| Symbol | Trades | W | L | Net PnL |
|---|---:|---:|---:|---:|
| AUDUSD | 2 | 2 | 0 | +3.60 |
| EURUSD | 1 | 1 | 0 | +2.19 |
| GBPJPY | 1 | 1 | 0 | +0.17 |
| GBPUSD | 1 | 1 | 0 | +3.12 |
| NZDUSD | 2 | 1 | 1 | -5.71 |
| USDJPY | 4 | 4 | 0 | +0.75 |
| XAUUSD | 1 | 0 | 1 | -6.60 |

## Position Review

### EURUSD SELL `9380318417`

- PnL: +2.19 USD.
- Duration: 56.2 min.
- Realized: +2.43 pips.
- MFE / MAE: +7.0 / -10.9 pips.
- Captured MFE: 34.8%.
- Verdict: winner, but exit quality was mediocre. The position survived more
  adverse movement than profit captured.
- Lesson: this is not a good candidate for more size at entry. If it scales, it
  should scale only after MFE confirmation and low MAE.

### USDJPY BUY `9382346538`

- PnL: +0.51 USD.
- Duration: 125.2 min.
- Realized: +8.3 pips.
- MFE / MAE: +12.9 / -3.4 pips.
- Captured MFE: 64.3%.
- Verdict: good controlled winner.
- Lesson: this is the kind of trade where winner management worked reasonably.
  It did not need aggressive extra size, but it supports letting strong winners
  run modestly longer when MAE is low.

### GBPUSD BUY `9384183653`

- PnL: +3.12 USD.
- Duration: 41.3 min.
- Realized: +2.4 pips.
- MFE / MAE: +3.8 / -0.9 pips.
- Captured MFE: 63.2%.
- Verdict: good scalp-style winner with clean low MAE.
- Lesson: candidate for small add-on only if spread stays clean and MFE expands
  beyond current small range.

### USDJPY BUY `9384440292`

- PnL: +0.08 USD.
- Duration: 33.2 min.
- Realized: +1.3 pips.
- MFE / MAE: +4.9 / -2.7 pips.
- Captured MFE: 26.5%.
- Verdict: weak small winner.
- Lesson: the trade left pips on the table, but MAE was not clean enough to
  justify larger size.

### USDJPY BUY `9384866526`

- PnL: +0.09 USD.
- Duration: 13.9 min.
- Realized: +1.4 pips.
- MFE / MAE: +3.0 / -0.4 pips.
- Captured MFE: 46.7%.
- Verdict: small but clean winner.
- Lesson: acceptable protection; not enough MFE to justify scaling.

### AUDUSD SELL `9384423865`

- PnL: +2.64 USD.
- Duration: 87.9 min.
- Realized: +2.93 pips.
- MFE / MAE: +6.1 / -0.9 pips.
- Captured MFE: 48.1%.
- Verdict: good structure and low adverse movement. The exit protected profit,
  but it also left about half the favorable excursion behind.
- Lesson: strong candidate for improved runner logic or later partial-trailing
  calibration. Add-on only after proof, not at entry.

### NZDUSD SELL `9385211513`

- PnL: +2.87 USD.
- Duration: 2.0 min.
- Realized: +2.21 pips.
- MFE / MAE: +3.0 / -0.6 pips.
- Captured MFE: 73.6%.
- Verdict: very fast clean winner.
- Lesson: good profit capture, but the short duration means it is not enough
  evidence for larger size by itself.

### USDJPY BUY `9385381831`

- PnL: +0.07 USD.
- Duration: 72.5 min.
- Realized: +1.2 pips.
- MFE / MAE: +1.4 / -3.0 pips.
- Captured MFE: 85.7%.
- Verdict: tiny winner after poor excursion profile.
- Lesson: high capture percentage is misleading because total MFE was tiny.
  This should not influence scaling confidence.

### GBPJPY BUY `9385405800`

- PnL: +0.17 USD.
- Duration: 76.3 min.
- Realized: +2.7 pips.
- MFE / MAE: +5.6 / -2.4 pips.
- Captured MFE: 48.2%.
- Verdict: acceptable but not strong.
- Lesson: moderate MFE with meaningful MAE. Do not scale early.

### AUDUSD SELL `9385232966`

- PnL: +0.96 USD.
- Duration: 133.6 min.
- Realized: +1.6 pips.
- MFE / MAE: +2.9 / -3.5 pips.
- Captured MFE: 55.2%.
- Verdict: small winner, but adverse movement exceeded favorable movement.
- Lesson: should not be treated as high-confidence. It survived more than it
  dominated.

### XAUUSD BUY `9386220512`

- PnL: -6.60 USD.
- Duration: 25.3 min.
- Realized: -660 pips.
- MFE / MAE: +335 / -715 pips.
- Entry: 4045.22.
- Exit: 4038.62.
- Broker close: SL.
- Log evidence:
  - Risk firewall allowed projected loss about 6.61 USD and projected gain
    about 13.21 USD.
  - Order opened at the minimum lot, volume 0.01.
  - Portfolio overlap de-score reduced risk but did not block.
- Verdict: normal SL technically, but not a harmless loss. XAUUSD can move
  enough to erase many small FX wins.
- Lesson: XAUUSD needs a separate stricter risk and timing profile. It should
  not share the same tolerance logic as small FX scalps.

Recommended action:

- Add a gold-specific "volatility shock / adverse impulse" filter before entry.
- Consider lower risk or stricter confirmation for XAUUSD.
- Do not allow winner scaling on XAUUSD until more clean winner evidence
  exists after this loss.

### NZDUSD SELL `9385213319`

- PnL: -8.58 USD.
- Duration: 229.5 min.
- Realized: -6.6 pips.
- MFE / MAE: 0.0 / -7.5 pips.
- Close comment: `mt5bot_close_ioc`.
- Log evidence:
  - Time stop closed stale position after about 49.5 minutes in the active
    symbol cycle, with profit around -6.7 pips.
- Verdict: this was worse than a normal small failed scalp because MFE never
  became favorable. It sat against the position and then time-stop closed.
- Lesson: if MFE is still zero after a defined early window, the system should
  reduce faster or exit earlier. Waiting until time-stop can turn a no-go setup
  into a full-size drag.

Recommended action:

- Add an early "no favorable excursion" rule:
  - if MFE <= 0 after N bars/minutes and MAE exceeds a fraction of SL, reduce or
    exit before the full time stop.
- Add a "second entry same symbol after just closed winner" caution. This losing
  NZDUSD trade opened immediately after a profitable NZDUSD short closed. It
  may be a continuation attempt after the move had already paid.

## Cross-Trade Lessons

### 1. High Win Rate Is Not Enough

10 winners produced +12.70 USD, but 2 losers lost -15.18 USD. This means the
system can be right often and still lose net if loss size is not controlled
relative to average win.

### 2. Winner Scaling Must Be Selective

Only some winners had a profile that could justify more size:

- Best candidates: USDJPY `9382346538`, GBPUSD `9384183653`, AUDUSD
  `9384423865`, NZDUSD `9385211513`.
- Weak/non-candidates: EURUSD `9380318417`, AUDUSD `9385232966`, small USDJPY
  wins with tiny MFE.

The system should require:

- MFE above a minimum threshold.
- Low MAE/MFE ratio.
- Current price still near MFE.
- Clean spread/ATR.
- Portfolio heat below threshold.

### 3. Gold Needs Separate Governance

XAUUSD risk is not comparable to a small FX scalp. Even at 0.01 lot, one gold
SL can erase many small FX wins. It needs symbol-specific:

- entry quality gates,
- news/session filters,
- risk cap,
- and scaling restrictions.

### 4. Add Early Failure Detection

NZDUSD loss had MFE of 0.0 pips and MAE of 7.5 pips. That is a clean signal
that the market never confirmed the trade.

Proposed rule:

- If a trade has no favorable excursion after an early window and has already
  consumed a meaningful part of SL distance, reduce or exit before full time
  stop.

### 5. Need Portfolio Heat Engine

The reviewed losses happened while the system had multiple positions and recent
profit. The next step is not simply reducing all risk; it is measuring account
heat:

- total projected loss to SL,
- open risk by symbol,
- exposure by currency/theme,
- live drawdown,
- and current realized session PnL.

### 6. Need Live Position Supervisor

This review reinforces the enterprise plan: position management should not be a
side effect of the entry-rotation loop. A dedicated supervisor should watch all
open positions and react to:

- no favorable excursion,
- fast adverse impulse,
- missed profit-lock,
- stale positions,
- missing SL/TP,
- and add-on eligibility.

## Current Live State During Review

At one live check during this review:

- Balance: 3007.95 USD.
- Equity: 3005.28 USD.
- Floating PnL: -2.67 USD.
- Open positions: 3.
- Pending orders: 0.

Open positions then observed:

- `USDJPY` BUY 0.01, slight floating profit.
- `EURUSD` SELL 0.08, floating loss around -3.28 USD.
- `GBPUSD` BUY 0.06, floating profit around +0.60 USD.

No live trades were opened, closed, or modified manually during this review.

## Recommended Next Changes

Do not activate changes while positions are live. Prepare externally and apply
only in a clean MT5 window.

Priority 1:

- Build Live Position Supervisor.

Priority 2:

- Build Portfolio Heat Engine in report-only mode.

Priority 3:

- Add early no-MFE / adverse-excursion rule:
  - no favorable excursion after N bars/minutes;
  - MAE consumed > configured fraction of SL;
  - action: reduce or exit depending on config.

Priority 4:

- Add symbol-specific stricter XAUUSD profile:
  - lower max add-on permission,
  - stricter ADX/spread/ATR gate,
  - volatility shock filter,
  - and no winner scaling until enough clean evidence.

Priority 5:

- Upgrade post-trade review to always reconstruct MFE/MAE directly from MT5
  bars, because the current automatic reports still show `n/a` for MFE/MAE in
  several cases.

## Verdict

The agent is doing many things right: high hit rate, broker-side protection,
profit-lock behavior, overlap blocking, and fast rotation. But the newest
closed trades show the exact reason the enterprise architecture is needed:

- small wins are frequent,
- bigger losses still happen,
- and live-position management needs to be more independent, faster, and more
account-aware.

The next serious implementation should be the Live Position Supervisor plus
Portfolio Heat reporting, not more markets and not more size.
