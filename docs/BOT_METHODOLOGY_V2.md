# Bot Methodology V2

This is the new methodology standard for paused-bot redesign. It replaces the idea of running the same EMA crossover template across every symbol.

## Core Principle

No bot trades because an indicator crossed. A bot trades only when these layers align:

1. Market state
2. Location
3. Confirmation
4. Risk/invalidation
5. Expected payoff
6. Session fit

If one layer is missing, the bot stays flat.

## Layer 1 - Market State

Allowed states:

- Balance: price is rotating around fair value; breakout chasing is usually bad.
- Imbalance up: buyers are moving price away from value.
- Imbalance down: sellers are moving price away from value.
- Unknown: no trade.

Implementation:

- classify_market_state in src/mt5_bot/market_structure.py.
- Use ATR-adjusted range/displacement, not visual guessing.

## Layer 2 - Location

Allowed locations:

- VWAP / anchored VWAP pullback.
- Prior range edge.
- Approximate LVN/HVN/POC from tick-volume profile.
- Reclaim back into value after failed breakout.

Disallowed:

- Mid-range entries.
- Breakout tick chasing.
- Generic EMA cross without value context.

## Layer 3 - Confirmation

Ideal source:

- Footprint, CVD, stacked imbalance, absorption.

MT5 proxy source:

- Candle rejection.
- Close reclaim.
- Tick-volume pressure.
- Spread not elevated.
- M1/M5 follow-through after level touch.

Important:

- MT5 proxies are not the same as futures order flow. They require stricter validation.

## Layer 4 - Risk And Invalidation

Rules:

- Default research risk: 0.10% to 0.25%.
- Stop must sit at structural invalidation.
- No widening stops.
- If wrong, the trade should fail quickly.
- Max 2 attempts per idea.
- Max 3 stop-outs per day per model.
- No live promotion without positive expectancy.

## Layer 5 - Expected Payoff

A bot must pass:

- Positive expectancy.
- Profit factor above 1.25.
- Average win/loss not structurally inverted.
- Loss concentration controlled.
- Sample size: 20-50 clean forward trades before production.

## Layer 6 - Session Fit

Every bot must prove which session it belongs to:

- Tokyo
- London
- NY
- London/NY overlap

No 24h default unless data proves it.

## Model A - Trend Continuation

Use when:

- Market state is imbalance up/down.
- Price pulls back to VWAP/AVWAP or profile location.
- Confirmation appears in trend direction.

Entry:

- Pullback rejection in direction of imbalance.

Invalidation:

- Beyond failed level or ATR structural stop.

Target:

- Next value area / POC / HTF level / fixed R multiple if profile target is unavailable.

## Model B - Value Reclaim / Mean Reversion

Use when:

- Market is balanced.
- Breakout outside range fails.
- Price reclaims value.

Entry:

- Pullback after reclaim, or close back inside value with confirmation.

Invalidation:

- Beyond failed auction high/low.

Target:

- POC or VWAP.

## Bot Decisions From First Research Pass

- Current winners are not redesigned while they continue to pass live-health checks.
  USDCHF, XAUUSD main, and GBPJPY remain in the reduced forward test with their current working methodology and reduced risk caps.
  Methodology V2 applies first to paused/rejected bots and any future candidates.
- For the full 12-bot individual methodology audit, see docs/BOT_12_INDIVIDUAL_AUDIT.md.
- USDJPY: only research candidate so far; must split Tokyo vs NY before sandbox.
- NZDUSD: near but below PF gate; do not promote.
- EURUSD: rejected under EMA and first value/imbalance proxy.
- GBPUSD: rejected; winrate issue remains payoff/expectancy.
- USDCAD: rejected/more data.
- XAUUSD_M5: rejected; gold M5 needs a more specialized model or stays retired.
- AUDUSD: rejected.
- XAGUSD: rejected.

## Promotion Path

1. Research backtest.
2. Session split.
3. Non-live candidate config.
4. Dry-run/sandbox.
5. One bot at a time into reduced forward test.
6. Only after clean sample, consider main suite.
