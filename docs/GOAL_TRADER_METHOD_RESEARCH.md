# /goal - Trader Method Research And Bot Restructure

Date: 2026-05-19
Repo: C:\Users\jean_\Desktop\mt5_trading_bot
Branch observed: claude/work

## Objective

Research the requested traders deeply enough to convert public, verifiable methodology into testable bot rules. Then restructure or replace the paused bots only after the rules pass backtest and forward-test gates.

This is analysis and system design, not a live-trading recommendation.

## Current Live Constraint

The reduced forward test remains separate and should not be disrupted:

- Active: USDCHF, XAUUSD main, GBPJPY.
- Paused: EURUSD, GBPUSD, NZDUSD, USDCAD, XAUUSD_M5, USDJPY, USDJPY_ASIA, AUDUSD, XAGUSD.
- No paused bot gets reactivated until research, backtest, and forward-test criteria pass.

## Source Quality Rule

- Use public sources only.
- Separate verified public methodology from marketing claims.
- Do not attribute a rule to a trader unless the source actually supports it.
- If a requested trader cannot be identified reliably, mark that part BLOCKED instead of inventing.

## Fabio Valentini - Publicly Supported Methodology

Public sources found:

- TradeZella: Auction Market Strategy, attributed to Fabio's Auction Market Theory + LVN playbook.
- Forex.in.rs article summarizing Fabio Valentini's order-flow/VWAP playbook and interview notes.
- Fabervaale ENG YouTube channel exists and includes risk/orderflow topics, but direct transcript extraction was not completed in this pass.

Core methodology extracted:

1. Instrument focus
   - Primarily futures scalping, especially NASDAQ/NQ during New York liquidity.
   - Secondary ES when NQ is messy; occasional Gold only with A-quality confluence.
   - This is not originally a generic forex M5 EMA method.

2. Market state first
   - Distinguish balance from imbalance.
   - Balance: price rotates around fair value; breakouts often fail.
   - Imbalance: aggressive movement away from value seeking a new fair value.
   - No clear state means no trade.

3. Location second
   - Use Volume Profile levels: POC, HVN, LVN.
   - Use VWAP/AVWAP as fair-value/gravity levels.
   - Avoid mid-range entries.
   - Prefer pullbacks into LVN/VWAP/range edge after structure forms.

4. Aggression/confirmation third
   - Original method uses order flow/footprint/CVD/stacked imbalances/absorption.
   - In MT5 forex, we usually do not have true futures footprint or order-book aggression.
   - Any forex/CFD implementation must use proxies: tick volume, candle displacement, wick rejection, close reclaim, spread behavior, and M1/M5 momentum.

5. Two models
   - Trend continuation: out-of-balance move, pullback to LVN/VWAP, confirmation in trend direction, target next value/POC or HTF level.
   - Mean reversion: failed breakout outside balance, reclaim back inside value, pullback to reclaim leg/LVN, target POC.

6. Risk model
   - Small risk per trade, around 0.25% to 0.5%.
   - Stop beyond aggression/failed auction, not widened.
   - If wrong, trade should fail quickly.
   - Stop after repeated stop-outs; quality over quantity.
   - Scale only after proven green session/week, not before.

7. Journal/statistics
   - Track setup class A/B/C.
   - Track expectancy by setup, session, hour, level type, and exit reason.
   - Size up only on A setups with positive expectancy.

## Patrick Nill - Current Evidence Status

Status: BLOCKED / identity not verified.

Searches for Patrick Nill trading/trader/forex/futures/order flow/ICT did not return a reliable public trader methodology. Bing results for exact-name searches were unrelated name-definition pages. DuckDuckGo blocked with anti-bot challenge. OpenClaw search provider also failed on several exact queries.

Current decision:

- Do not invent a Patrick Nill methodology.
- Ask Jean for a link, handle, course name, screenshot, video, or corrected spelling.
- If Jean confirms he meant another Patrick, restart this section with exact-source research.

## Why The Paused Bots Lost

The paused bots are not just unlucky. Their current shared method is too generic:

- EMA 5/13 M5 crossover is used across too many symbols.
- Session filters are too broad.
- Retest/candle confirmation is not consistently enforced.
- ADX/range regime is not enough to distinguish auction balance from imbalance.
- GBPUSD and NZDUSD show the key failure: win rate can be high while expectancy is negative because average loss is larger than average win.
- EURUSD had a direct post-fix failure: 3 losses out of 3 since 2026-05-15.

## Restructure Direction

Do not simply retune EMAs. Build a separate research layer:

1. Market-state engine
   - Balance / imbalance classification.
   - VWAP / anchored VWAP.
   - Approximate volume profile from tick volume where true order flow is unavailable.

2. Setup engine
   - Trend continuation model.
   - Failed-breakout mean-reversion model.
   - A/B/C quality scoring.

3. Risk engine
   - 0.10% to 0.25% research risk in forward test.
   - Max 2 failed attempts per idea.
   - Max 3 stop-outs/day per model.
   - No reactivation into production until sample gate is met.

4. Analytics
   - Expectancy by symbol, setup, session, regime, and quality class.
   - Average win/loss and loss concentration.
   - MFE/MAE if available or approximated from position metrics.

## Bot Decisions

### EURUSD

Decision: replace current EMA bot with a mean-reversion/value-reclaim candidate only.

Reason:

- Current trend-following M5 EMA failed post-fix.
- EURUSD often mean-reverts in liquid sessions unless there is clear catalyst/displacement.

Candidate:

- Session: London/NY overlap only.
- Setup: failed breakout from balance, reclaim value, pullback to reclaim leg.
- Target: POC/VWAP.
- No trade in mid-range.

### GBPUSD

Decision: redesign, not re-enable.

Reason:

- Win rate is misleading; average loss overwhelms average win.

Candidate:

- Use A/B/C setup quality.
- Disable early partials until backtest proves they help.
- Require structure + VWAP/AVWAP level + candle/tick-volume confirmation.

### NZDUSD

Decision: redesign or retire if sample stays weak.

Reason:

- Similar expectancy failure to GBPUSD, but lower evidence.

Candidate:

- Fewer sessions, stricter spread/ATR filter.
- Mean-reversion candidate only unless imbalance is objectively detected.

### USDCAD

Decision: keep paused.

Reason:

- Insufficient post-fix evidence and negative result.

Candidate:

- Only re-test around NY session and oil/USD catalyst-aware windows.

### XAUUSD_M5

Decision: do not re-enable current M5 gold method.

Reason:

- Gold M5 is too volatile for generic EMA.

Candidate:

- If rebuilt, use Fabio-style trend continuation only: imbalance plus pullback to VWAP/LVN proxy.
- Separate hard lot cap and smaller risk than FX.

### USDJPY / USDJPY_ASIA

Decision: pause until session model is rebuilt.

Reason:

- Current contribution is negligible or negative.

Candidate:

- Tokyo-specific mean-reversion or NY trend continuation, not mixed 24h behavior.

### AUDUSD / XAGUSD

Decision: keep paused until ranked by research engine.

Reason:

- No current proof that they deserve capital.

## Implemented In This Pass

- Added src/mt5_bot/market_structure.py:
  - anchored_vwap
  - volume_profile
  - classify_market_state
- Added tests/test_market_structure.py.
- Added src/mt5_bot/research_strategy.py:
  - trend_continuation proxy
  - value_reclaim proxy
  - setup quality labels
- Added src/mt5_bot/research_backtest.py.
- Added scripts/research_backtest.py.
- Added tests/test_research_strategy.py.

These are research utilities only. They are not wired to live execution yet.

## First Research Backtest Results

Short corrected window, 2026-05-15 to 2026-05-20:

- No paused bot passed.
- EURUSD, AUDUSD, NZDUSD, USDJPY printed small losing samples.
- GBPUSD, USDCAD, XAUUSD_M5, XAGUSD had zero accepted setups under the first strict proxy.

Longer research window, 2026-04-15 to 2026-05-20:

| Symbol | Trades | Net pips | Expectancy | PF | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| USDJPY | 19 | 42.77 | 2.25 | 1.52 | research candidate only |
| NZDUSD | 14 | 5.85 | 0.42 | 1.19 | reject/more data |
| EURUSD | 12 | -2.77 | -0.23 | 0.91 | reject |
| GBPUSD | 13 | -19.48 | -1.50 | 0.53 | reject |
| AUDUSD | 12 | -11.43 | -0.95 | 0.66 | reject |
| USDCAD | 8 | -8.31 | -1.04 | 0.58 | reject |
| XAUUSD_M5 | 7 | -644.14 | -92.02 | 0.80 | reject |
| XAGUSD | 7 | -198.62 | -28.37 | 0.00 | reject |

Interpretation:

- USDJPY is the only symbol that deserves a sandbox candidate from this research pass.
- NZDUSD is close but does not pass the PF gate.
- Metals M5 and silver remain clearly unfit under this proxy.
- EURUSD/GBPUSD remain rejected; changing from EMA to first-pass value/imbalance proxy is not enough.
- The duplicated USDJPY row came from both JPY configs sharing the same symbol; the strategy candidate must later split by session before any forward test.

## Gates Before Reactivating Any Paused Bot

1. Source gate
   - Fabio methodology: PASS enough for first research implementation.
   - Patrick Nill methodology: BLOCKED until Jean provides exact source/identity.

2. Code gate
   - Market structure and research backtest utilities compile and tests pass.

3. Backtest gate
   - Each redesigned bot must show positive expectancy, PF > 1.25, and average win/loss not structurally inverted.

4. Forward-test gate
   - 20-50 clean trades per model group.
   - No risk-cap breach.
   - No hidden crash loop or stale reporting.

5. Production gate
   - Only one redesigned bot joins reduced mode at a time.

## Next Engineering Steps

1. DONE: Split USDJPY research candidate by session.
2. DONE: Create non-live USDJPY London V2 research config.
3. Add report columns: setup_type, market_state, vwap_distance, profile_level_type, setup_quality.
4. Add setup-level breakdown to research_backtest.json.
5. Gather more USDJPY London sample or run sandbox before any live promotion.
6. Keep EURUSD, GBPUSD, NZDUSD, USDCAD, XAUUSD_M5, AUDUSD, XAGUSD paused/rejected until a stronger model appears.
