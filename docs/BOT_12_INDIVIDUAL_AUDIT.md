# 12-Bot Individual Methodology Audit

Date: 2026-05-19
Scope: valid trade window from 2026-05-15 onward, per Jean's correction.
Source of PnL: MT5 history by magic via scripts/suite_status_report.py.

## Executive Conclusion

The current 12-bot suite is not truly 12 different methodologies. Most bots are the same base template:

- M5 EMA 5/13 crossover.
- H1 or M15/M30 trend EMA filter.
- RSI guard.
- ATR gate and ATR SL/TP.
- ADX filter.
- 24h session filter.
- partial close + trailing.

That explains the portfolio behavior: the suite was broad, but not diversified. It repeated one logic across many symbols. Some symbols paid, others exposed that the template does not fit their regime.

The new rule is:

- Keep working winners running only while their live health and expectancy remain acceptable.
- Do not redesign a winner just because we are redesigning losers.
- Every paused/rejected bot must earn its place with a symbol-specific methodology, session, and payoff model.
- If a symbol cannot produce meaningful returns for a 90k account with controlled risk, retire or replace it.

## Current Live Reduced Suite

Active now:

- XAUUSD main
- USDCHF
- GBPJPY

Paused/rejected:

- EURUSD
- GBPUSD
- USDJPY main
- AUDUSD
- XAUUSD_M5
- USDCAD
- NZDUSD
- XAGUSD
- USDJPY_ASIA

## Performance Since 2026-05-15

| Bot | Magic | PnL | Closed | PF | Expectancy | Initial decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| XAUUSD main | 260436 | 10582.05 | 2 | n/a | 5291.03 | keep, but watch sample size |
| USDCHF | 260446 | 1563.62 | 7 | 3.00 | 223.37 | keep |
| GBPJPY | 260443 | 5.64 | 9 | 3.29 | 0.63 | keep only as low-risk scout |
| USDJPY main | 260435 | -3.37 | 3 | 0.22 | -1.12 | research candidate only |
| USDJPY Asia | 260445 | -3.66 | 1 | 0.00 | -3.66 | paused |
| NZDUSD | 260442 | -395.04 | 3 | 0.42 | -131.68 | paused, maybe research later |
| GBPUSD | 260434 | -433.80 | 8 | 0.68 | -54.22 | paused/redesign |
| USDCAD | 260441 | -482.42 | 1 | 0.00 | -482.42 | paused |
| XAUUSD_M5 | 260440 | -603.84 | 1 | 0.00 | -603.84 | reject current method |
| EURUSD | 260433 | -1936.63 | 3 | 0.00 | -645.54 | reject current method |
| AUDUSD | 260437 | no post-window closed PnL in status report | 0 | n/a | n/a | paused/no evidence |
| XAGUSD | 260444 | no post-window closed PnL in status report | 0 | n/a | n/a | paused/no evidence |

## Bot-By-Bot Methodology Review

### 1. XAUUSD main - keep, not proven enough to scale

Current method:

- M5 EMA 5/13 trend-following with M15 trend filter.
- ATR and ADX gates.
- Large ATR threshold for gold.
- Current reduced risk: 0.25%, max_order_volume 0.5, ADX 24.

Assessment:

- It produced the majority of the suite profit.
- But the sample is only 2 closed profitable deals in the corrected window.
- The result is excellent, but not enough to declare the methodology permanently solved.

Decision:

- Keep running in reduced mode.
- Do not redesign now.
- Do not scale until more clean trades confirm repeatability.
- Report separately from FX because gold PnL dominates the dashboard.

Future methodology if it weakens:

- Fabio-style imbalance + VWAP/LVN pullback for gold.
- No generic 24h M5 chasing.

### 2. USDCHF - keep

Current method:

- M5 EMA 5/13 with H1 trend filter.
- ADX now stricter at 22.
- Reduced risk 0.35%.

Assessment:

- Best non-gold bot in corrected window.
- PF 3.00, expectancy positive.
- Still has one large loss relative to average win, so payoff must be watched.

Decision:

- Keep running.
- No redesign unless expectancy deteriorates.
- Candidate for continued forward test.

### 3. GBPJPY - keep only as scout

Current method:

- M5 EMA 5/13 with H1 trend filter.
- ADX now stricter at 24.
- Reduced risk 0.25%.

Assessment:

- PF is positive, but absolute PnL is tiny for a 90k account.
- This bot may be statistically stable but economically weak.

Decision:

- Keep running only because risk is low and PF is positive.
- It must prove that it can generate meaningful return, not just avoid losses.
- If it stays tiny after enough sample, replace or redesign.

### 4. USDJPY main - research candidate, not live yet

Current method:

- Same EMA 5/13 M5 template.
- 24h session.

Assessment:

- Corrected live window is slightly negative.
- But the first research backtest using market-state/VWAP/profile proxies showed the only promising paused-bot result: 19 trades, +42.77 pips, PF 1.52, expectancy +2.25 over 2026-04-15 to 2026-05-20.

Decision:

- Do not restore current EMA bot.
- Build a USDJPY-specific V2 candidate.
- Split by session first.

Session split result, 2026-04-15 to 2026-05-20:

- Tokyo: 4 trades, -1.87 pips, PF 0.83, reject.
- London: 8 trades, +36.12 pips, expectancy +4.52, PF 1.99, research candidate but sample too small.
- London/NY overlap: 2 trades, -12.80 pips, reject.
- NY: 3 trades, -22.11 pips, reject.
- All sessions: 19 trades, +42.77 pips, PF 1.52.

Methodology direction:

- USDJPY V2 should not be Tokyo or NY first.
- The only defensible candidate is London-session only.
- Because London sample is only 8 trades, it remains non-live until more history/sandbox validation.

Artifact:

- config/research_usdjpy_london_v2.yaml created as a research-only candidate with trade_enabled false and magic 260545.

Setup breakdown:

- London trend_continuation B: 3 trades, +37.18 pips, expectancy +12.39, PF 4.12.
- London trend_continuation A: 5 trades, -1.06 pips, expectancy -0.21, PF 0.96.

Judge note:

- This is promising but not ready for live.
- The fact that B outperforms A means the quality scoring is not calibrated yet.
- Before promotion, either recalibrate quality labels or require more sample proving the setup is real.

### 5. USDJPY Asia - paused

Current method:

- Same EMA 5/13 M5 logic with M30 trend filter.
- Not actually session-specialized enough despite the name.

Assessment:

- Corrected window has a loss and too little sample.

Decision:

- Keep paused.
- Merge its future work into the USDJPY session-split candidate.

### 6. NZDUSD - near but not enough

Current method:

- EMA 5/13 M5 with M30 trend filter.
- 24h session.

Assessment:

- Corrected live window negative.
- Longer V2 research proxy showed slight positive net pips but PF 1.19, below the 1.25 minimum gate.

Decision:

- Keep paused.
- Do not promote.
- Revisit only after USDJPY candidate is completed.

Likely methodology:

- Session-restricted value-reclaim only.
- No broad 24h trend bot.

### 7. GBPUSD - reject current method

Current method:

- EMA 5/13 M5 with H1 trend filter.
- 24h session.

Assessment:

- High-ish win rate but negative expectancy.
- This is the classic bad payoff problem: small wins, large losses.

Decision:

- Keep paused.
- Current methodology is not acceptable.

Future methodology:

- London/NY overlap only.
- Value/reclaim or VWAP-location model.
- Disable early partial close until backtest proves it improves expectancy.

### 8. EURUSD - reject current method

Current method:

- EMA 5/13 M5 with H1 trend filter.
- 24h session.

Assessment:

- Failed directly in corrected live window: 3 losses out of 3.
- Research proxy also did not rescue it.

Decision:

- Keep paused.
- Replace methodology, not tune current one.

Future methodology:

- Mean-reversion/value-reclaim candidate only.
- London/NY overlap.
- No mid-range entries.

### 9. USDCAD - paused/no evidence

Current method:

- EMA 5/13 M5 with H1 trend filter.
- 24h session.

Assessment:

- Negative and too little evidence.
- First V2 research pass rejected it.

Decision:

- Keep paused.
- Retest only if using CAD/oil/session-aware filters.

### 10. AUDUSD - paused/no evidence

Current method:

- EMA 5/13 M5 with H1 trend filter.
- 24h session.

Assessment:

- No useful corrected-window closed PnL in status report.
- Longer research proxy negative.

Decision:

- Keep paused.
- Low priority.

### 11. XAUUSD_M5 - reject current method

Current method:

- Separate XAUUSD M5 bot with looser threshold than main gold.
- Same generic EMA structure.

Assessment:

- Negative corrected window.
- Research proxy strongly negative.
- Running both XAUUSD main and XAUUSD_M5 risks duplicated gold exposure.

Decision:

- Keep rejected.
- Do not run beside XAUUSD main unless it becomes a clearly different model.

Future methodology:

- Only rebuild as gold-specific imbalance/VWAP/LVN model with hard caps.

### 12. XAGUSD - paused/no evidence

Current method:

- Generic EMA M5 adapted to silver.

Assessment:

- No useful corrected-window closed PnL.
- Longer V2 proxy negative.
- Silver spread/volatility makes generic M5 fragile.

Decision:

- Keep paused.
- Low priority unless a metals-specific model is built.

## Economic Filter For 90k Account

Jean's point is correct: a bot that earns 500 or 1000 may still be weak if it consumes risk, margin, attention, or drawdown budget.

New economic gate:

- Positive expectancy is required but not sufficient.
- Profit must be meaningful relative to risk budget.
- A low-PnL bot can remain only if it is a low-risk scout with high PF and low drawdown.
- If it cannot scale safely or contribute meaningfully, replace it.

Current interpretation:

- XAUUSD main contributes meaningfully.
- USDCHF contributes meaningfully enough to keep testing.
- GBPJPY is not yet economically convincing; keep temporarily due PF, but do not scale.

## Implementation Plan

1. Keep current winners running in reduced mode.
2. Build USDJPY V2 session split: Tokyo mean-reversion vs NY trend-continuation.
3. Add setup/session attribution to reports.
4. Backtest USDJPY candidate.
5. If USDJPY passes, forward-test it as the only added bot.
6. Revisit NZDUSD after USDJPY.
7. Reject or replace EURUSD, GBPUSD, USDCAD, AUDUSD, XAUUSD_M5, XAGUSD unless a new model passes gates.

## Current Operating Decision

Do not return to a 12-bot suite yet.

Run:

- XAUUSD main
- USDCHF
- GBPJPY

Research:

- USDJPY V2 candidate first.

Paused:

- Everything else.
