# Trade Day Audit - 2026-05-18

Scope: read-only audit after Jean asked why the suite gave back gains and how to improve. Suite was already stopped. No orders were opened, closed, or modified.

Data window used: `2026-05-18T05:00:00` to `2026-05-19T05:00:00` from local SQLite `data/pro*.sqlite`, approximating 2026-05-18 America/Lima.

## Account Result

- First balance snapshot: `91449.18`
- Last balance snapshot: `89959.13`
- Net day change: `-1490.05`
- Open positions at stop/status check: `0`
- Recent log errors at stop/status check: `0`

## Trade Result Summary

- Closed trade groups: `13`
- Wins: `8`
- Losses: `5`
- Win rate: `61.5%`
- Gross wins: `+1249.12`
- Gross losses: `-2739.17`
- Net PnL: `-1490.05`
- Average win: `+156.14`
- Average loss: `-547.83`
- Payoff ratio: `0.29`

Core finding: the suite can be right more often than wrong and still lose because winners are cut small by partial/trailing exits while losing trades take the full stop.

## Ranked Trade Groups

| Symbol | Position | Net PnL | Notes |
|---|---:|---:|---|
| EURUSD | 8686148368 | -752.22 | full SL |
| EURUSD | 8679018862 | -722.40 | full SL |
| GBPUSD | 8679018784 | -659.00 | full SL |
| XAUUSD | 8682953344 | -603.84 | full SL |
| GBPJPY | 8685585902 | -1.71 | SL near flat |
| GBPJPY | 8686243257 | +0.62 | partial/trailing small win |
| USDJPY | 8679508229 | +0.94 | partial/trailing small win |
| GBPJPY | 8675370420 | +1.98 | partial/trailing small win |
| GBPJPY | 8679176957 | +4.51 | TP small lot |
| GBPUSD | 8686202462 | +136.00 | partial/trailing win |
| NZDUSD | 8682237304 | +281.76 | partial/trailing win |
| USDCHF | 8678430038 | +342.98 | partial/trailing win |
| GBPUSD | 8685395868 | +480.33 | partial/trailing win |

## Symbol Ranking

| Symbol | Net PnL |
|---|---:|
| EURUSD | -1474.62 |
| XAUUSD | -603.84 |
| GBPUSD | -42.67 |
| USDJPY | +0.94 |
| GBPJPY | +5.40 |
| NZDUSD | +281.76 |
| USDCHF | +342.98 |

## Root Causes

- `EURUSD` was the main damage: two full stop-losses totaled `-1474.62`, nearly the entire net daily loss.
- The suite allowed correlated USD exposure around the same window: `EURUSD` and `GBPUSD` opened at almost the same time and both hit SL, creating a combined drawdown of `-1381.40`.
- Full-loss size is materially larger than realized win size. The configured theoretical RR is 2.0, but actual exits do not behave like 2R because partial close/trailing often banks small profits and leaves few trades reaching full TP.
- No observed daily circuit breaker stopped new entries after the first major loss cluster. The suite continued and later took another EURUSD full SL.
- Reporting lag existed: latest report file was older than the DB/account snapshots, so live decisions should be made from DB/status until reporting is regenerated.

## Verdict

The bot did not fail because of one execution crash. The bigger issue is portfolio-level risk design: simultaneous correlated signals, full stop losses around `0.75%-1.0%` per trade, and small realized winners. This is not ready to scale aggressively.

To pursue aggressive growth, the suite needs guardrails first:

- Daily hard loss cap: stop new entries after `-1.0%` to `-1.5%` account loss.
- Correlation cap: do not allow simultaneous EURUSD + GBPUSD + NZDUSD directional USD exposure as independent full-risk trades.
- Bot kill-switch by symbol: pause a symbol after 1 full SL or 2 consecutive losses in the same day.
- Payoff repair: reduce partial close aggressiveness or require some trades to retain enough size for TP, otherwise average win remains too small.
- Ranking gate: only allocate normal risk to symbols with positive forward expectancy; reduce or disable EURUSD until it proves itself again.
- Reporting gate: regenerate reports after each suite stop and compare report PnL to account delta before trusting the report.

## Immediate Recommendation

Keep the suite stopped until these are implemented and validated:

- Daily loss circuit breaker.
- Correlated exposure limiter.
- Per-symbol pause after full SL.
- Report reconciliation that uses unique deal tickets and current DB snapshots.
- A forward-test rule: no scaling until at least 30-50 closed trades show positive expectancy after costs.

## Correction - MT5 Server-Day / Wider Window

Jean pointed out a missing gain from the trading-history screenshot. The original audit used Lima-day window
`2026-05-18T05:00:00` to `2026-05-19T05:00:00`, so it excluded the legacy XAUUSD TP that closed at
`2026-05-18T01:01:30+00:00` (2026-05-17 20:01 Lima).

When using a wider window that matches the visible MT5/server history, the missing trade is:

- XAUUSD position `8661985181`: `+9070.78`, comment `[tp 4540.46]`

Corrected broader-window result:

- Trades: `14`
- Net PnL: `+7580.73`
- Top gain: XAUUSD `8661985181`, `+9070.78`
- Main later losses remain: EURUSD `-1474.62`, XAUUSD `-603.84`, GBPUSD early loss `-659.00`

Interpretation: the account was still net positive across the wider history because of the legacy XAUUSD TP, but the same risk issue remains for the later bot session: average loss size and correlated USD exposure can give back a large part of the big win.
