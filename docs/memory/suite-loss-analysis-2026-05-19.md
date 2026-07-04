# Suite Loss Analysis - 2026-05-19

## Scope

Audit requested by Jean after stopping the live demo MT5 suite. This is technical and operational analysis, not financial advice or a recommendation to trade live.

Evidence sources:

- MT5 account history from 2026-05-01 through 2026-05-19.
- Live suite DBs under `C:\Users\jean_\Desktop\mt5_trading_bot\data\pro*.sqlite`.
- Live suite logs under `C:\Users\jean_\Desktop\mt5_trading_bot\logs`.
- Source/config inspection in `C:\Users\jean_\Desktop\mt5_trading_bot`.

Suite state before stop:

- 12/12 bot processes were running.
- MT5 connected and trade allowed.
- Balance/equity at stop check: 89,621.80 USD.
- Open positions: 0.
- Suite was later stopped and verified stopped.

## Headline Numbers

MT5 closed PnL from 2026-05-01 to 2026-05-19:

- Closed PnL: -9,473.74 USD.
- Closed PnL deals counted: 135.
- Main loss concentration: one XAUUSD loss of -17,102.36 USD on 2026-05-06/07.
- Last 48h closed PnL was positive at +7,261.21 USD, but the account remained below 100k due to earlier drawdown.

PnL by bot from MT5 history:

| Bot | Trades | W/L | PnL | Profit Factor | Exit notes |
| --- | ---: | ---: | ---: | ---: | --- |
| XAUUSD | 3 | 2/1 | -6,520.31 | 0.62 | One oversized SL loss dominated |
| EURUSD | 3 | 0/3 | -1,936.63 | 0.00 | All three exits by SL |
| AUDUSD | 1 | 0/1 | -1,221.34 | 0.00 | One large SL |
| XAUUSD_M5 | 2 | 0/2 | -766.44 | 0.00 | Both SL |
| USDCAD | 1 | 0/1 | -482.42 | 0.00 | One SL |
| GBPUSD | 10 | 7/3 | -475.30 | 0.66 | High win rate but losses larger than wins |
| NZDUSD | 3 | 2/1 | -395.04 | 0.42 | High win rate but one SL erased wins |
| OLD_EURUSD | 90 | 18/72 | -224.00 | 0.74 | Older small-trade system, structurally noisy |
| USDJPY_ASIA | 1 | 0/1 | -3.66 | 0.00 | Tiny SL |
| GBPJPY | 8 | 7/1 | +6.38 | 4.71 | Positive but tiny absolute edge |
| USDJPY | 6 | 3/3 | +981.40 | 1.45 | Positive due earlier big TP |
| USDCHF | 7 | 6/1 | +1,563.62 | 3.00 | Best current bot quality |

Daily PnL:

- 2026-04-30: -38.00
- 2026-05-01: -227.50
- 2026-05-05: +3,160.70
- 2026-05-06: -18,323.70
- 2026-05-07: -162.60
- 2026-05-08: -2,175.93
- 2026-05-15: +1,031.09
- 2026-05-17: +9,088.95
- 2026-05-18: -1,489.42
- 2026-05-19: -337.33

## Worst Losses

| Time Lima | Bot | Symbol | Volume | PnL | Exit |
| --- | --- | --- | ---: | ---: | --- |
| 05-06 20:02 | XAUUSD | XAUUSD | 8.27 | -17,102.36 | SL |
| 05-08 16:55 | USDJPY | USDJPY | 21.56 | -1,485.49 | SL |
| 05-06 19:00 | AUDUSD | AUDUSD | 15.46 | -1,221.34 | SL |
| 05-19 08:48 | USDCHF | USDCHF | 15.01 | -781.48 | SL |
| 05-18 21:17 | EURUSD | EURUSD | 13.93 | -752.22 | SL |
| 05-18 12:03 | EURUSD | EURUSD | 9.03 | -722.40 | SL |
| 05-08 16:19 | USDJPY | USDJPY | 21.63 | -690.44 | bot close |
| 05-19 04:33 | GBPUSD | GBPUSD | 10.11 | -677.37 | SL |
| 05-19 08:47 | NZDUSD | NZDUSD | 14.40 | -676.80 | SL |
| 05-18 12:03 | GBPUSD | GBPUSD | 6.59 | -659.00 | SL |
| 05-18 14:49 | XAUUSD_M5 | XAUUSD | 0.51 | -603.84 | SL |
| 05-19 05:16 | USDCAD | USDCAD | 18.42 | -482.42 | SL |
| 05-15 18:32 | EURUSD | EURUSD | 9.83 | -462.01 | SL |

## Root Causes

### 1. The loss distribution is dominated by tail events, not average losing trades

The single XAUUSD trade of -17,102.36 USD is larger than the entire positive contribution of the recent winning period. This indicates the suite was not failing slowly; it was exposed to one or two account-changing losses.

Specific XAUUSD case:

- Entry order: buy XAUUSD 8.27 lots at requested 4697.85.
- SL requested: 4685.53.
- Actual close price: 4677.14.
- Loss: -17,102.36.

The loss was worse than the nominal stop because execution happened far beyond the SL level. On gold, this is a major risk: stops are not guaranteed fills.

### 2. Position sizing was too large for demo challenge survival

Examples:

- XAUUSD 8.27 lots produced a -17.1k loss.
- AUDUSD 15.46 lots produced -1,221.34.
- USDJPY 21.56 lots produced -1,485.49.
- USDCAD 18.42 lots produced -482.42.
- GBPUSD 10.11 lots produced -677.37.

Even when the configured risk looks like 0.6%-0.75%, real risk can exceed intended risk because of symbol contract values, stop slippage, gold volatility, partial close behavior, and broker execution.

### 3. Gold is the main structural danger

XAUUSD and XAUUSD_M5 are the main account-damaging modules:

- XAUUSD: -6,520.31 net despite one +9,088.95 TP.
- XAUUSD_M5: -766.44 net in MT5 history, and its DB contains imported same-symbol historical XAUUSD losses that can confuse local reporting.
- Gold ATR/spread values are huge compared with FX pairs, and stop slippage on gold caused the largest loss.

### 4. High win rate did not equal positive expectancy

GBPUSD had 7 wins and 3 losses but still lost -475.30. NZDUSD had 2 wins and 1 loss but still lost -395.04.

Reason: partial wins were small, but full SL losses were large. The suite needs average win / average loss control, not just win-rate optimization.

### 5. Some entries triggered in mediocre signal quality

Recent entries show the bot accepting EMA crosses with ADX sometimes around 18-24 and RSI not strongly favorable. Examples:

- EURUSD 2026-05-18 21:49: ADX 18.17, RSI 58.83, risk_pct 0.75, then SL -752.22.
- USDJPY 2026-05-19 10:48: ADX 18.09, RSI 64.38, then SL -4.31.
- USDCAD 2026-05-19 07:05: ADX 23.72, RSI 54.76, then SL -482.42.

The suite appears too willing to trade a plain EMA cross unless later filters block it.

### 6. Crash loops degraded operational confidence

Logs showed repeated real errors:

- `NameError: name 'timedelta' is not defined` in multiple bots.
- `MT5 account_info failed: (-10001, 'IPC send failed')` in SILVER.

The watchdog restarted bots, but restart loops mean the suite can miss management windows, duplicate monitoring noise, or operate in degraded mode.

### 7. Local reporting can be polluted if not scoped carefully

The per-bot SQLite files do not perfectly equal per-bot PnL in MT5 history unless filtered by magic. Example: XAUUSD_M5 DB had imported same-symbol XAUUSD magic 260436 loss rows. Final performance reporting must use magic-scoped MT5 history as source of truth, with SQLite used as supporting telemetry.

## What Worked

- USDCHF showed the cleanest current behavior: +1,563.62, PF 3.00, 6 wins / 1 loss.
- USDJPY net positive due a large TP, but also had large historical risk.
- GBPJPY was stable but too small to matter: +6.38.
- Portfolio overlap de-score did trigger in some cases, but it was not enough to prevent correlated USD exposure.

## What Failed

- Gold risk was not survivable under stop slippage.
- Multiple FX bots opened large lot sizes around the same regime, compounding USD exposure.
- Partial-close/trailing design increased win rate optics but did not guarantee positive expectancy.
- Crash loops were tolerated instead of treated as a hard stop condition.
- Report totals are confusing unless MT5 history is filtered by magic.

## Plan

### Phase 0 - Keep Suite Stopped

Do not restart until Phase 1 is complete. Current state is not production-clean.

### Phase 1 - Code/ops fixes before any forward run

1. Fix `NameError: timedelta`.
2. Add a preflight check that fails hard if any bot throws an exception during startup/check.
3. Change monitoring status:
   - OK: all bots running, DB fresh, MT5 connected, no new critical errors.
   - DEGRADED: bots alive but warnings/crashes/IPC errors.
   - DANGEROUS: loss cap hit, margin risk high, repeated restarts, or reporting mismatch.
   - DOWN: no bot processes or MT5 disconnected.
4. Exclude `retcode_10009` from error counts; it is successful execution, not failure.
5. Build a magic-scoped report script and use MT5 history as PnL source of truth.

### Phase 2 - Risk reset

1. Disable XAUUSD and XAUUSD_M5 until gold-specific risk model is corrected.
2. Cap effective risk:
   - FX majors: max 0.25%-0.35% during forward test.
   - Gold: 0.10%-0.20% max if re-enabled later.
3. Add hard projected-loss firewall:
   - reject if broker-calculated SL loss exceeds configured account risk by more than 5%-10%.
   - reject if projected loss exceeds fixed USD cap.
4. Add day stop:
   - stop all bots at -1.0% account day loss.
   - stop a symbol at -0.5% account day loss.
5. Add weekly stop:
   - pause any bot after two full-SL losses or negative expectancy over a minimum sample.

### Phase 3 - Strategy filters

1. Do not trade plain EMA cross alone.
2. Require stronger regime confirmation:
   - ADX threshold by symbol/session.
   - trend alignment.
   - RSI not extended against the trade.
   - spread / ATR sanity.
3. Reduce duplicate USD exposure:
   - no simultaneous same-direction USD theme cluster unless risk is heavily reduced.
4. Review session filters:
   - rank symbols by session.
   - disable symbols that only win in one window.

### Phase 4 - Forward test protocol

Run only the best candidates first:

- Tier A: USDCHF, possibly GBPJPY.
- Tier B: USDJPY with small size only.
- Hold out: EURUSD, AUDUSD, USDCAD, NZDUSD until retested.
- Disabled: XAUUSD and XAUUSD_M5 until fixed.

Forward-test gate:

- 30 closed trades minimum per candidate.
- PF above 1.2 after costs/slippage.
- Average loss not larger than 1.2x planned loss.
- No single trade loss > 0.5% account.
- No critical runtime errors.

### Phase 5 - VPS/migration condition

Do not migrate the suite as-is. First:

1. Fix code.
2. Create `CODEX_RUNBOOK.md`.
3. Create `suite_report.py`.
4. Prove a 24h dry/demo run with:
   - no crash loops,
   - clean reports,
   - correct magic-scoped PnL,
   - no uncontrolled risk.

## Current Verdict

The suite was not merely unlucky. It had positive pockets, but the risk architecture allowed large tail losses, especially on gold. The correct next move is not to optimize entries first; it is to shrink and harden the risk/execution layer, then only re-enable symbols with evidence.

