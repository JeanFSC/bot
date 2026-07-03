# MT5 Payoff Skew Audit - 2026-07-02

Generated: 2026-07-02 17:30 America/Lima

## State

- Status label: WATCHLIST.
- Control room: OK.
- Supervisor: `demo_actions_enabled`, policy `portfolio_heat_allows_actions`.
- Current exposure at check: 2/2 known positions, unknown 0, unprotected 0.
- Current risk to SL at check: about 14.53 USD / 0.48% equity.
- Current positions at check:
  - AUDUSD BUY 0.09, entry 0.69197, current PnL about +0.27, MFE about +1.44 USD.
  - USDCAD SELL 0.13, entry 1.41810, current PnL about -2.11, MFE 0.00, MAE about -2.11 USD.

## What Happened

The bot is trading, but recent realized payoff is skewed: winners are small and full-stop losses are much larger.

Recent realized closed deals:

- AUDUSD +0.88
- AUDUSD +0.70
- AUDUSD +1.74
- AUDUSD +1.02
- GBPUSD -9.38
- USDCAD +1.55
- USDCAD +1.46

Rolling stats from the latest closed profit deals:

- Last 5: net -5.04, 4 wins avg +1.08, 1 loss avg -9.38, profit factor 0.46.
- Last 10: net -0.69, 8 wins avg +1.13, 2 losses avg -4.87, profit factor 0.93.
- Last 20: net +7.59, 18 wins avg +0.96, 2 losses avg -4.87, profit factor 1.78.
- Last 50: net +4.62, 45 wins avg +0.80, 5 losses avg -6.26, profit factor 1.15.

## Diagnosis

The issue is not order execution. Successful sends use `order_send_retcode_10009`, which is a successful MT5 execution.

The issue is expectancy/payoff shape:

- Configs target nominal R:R around 2.0.
- Losers can reach full SL.
- Winners are often harvested early by partial-close / profit-lock / trailing behavior before full TP.
- Current profit lock starts very early: `profit_lock_trigger_rr: 0.25`, `profit_lock_min_pips: 2.0`, `profit_lock_retrace_rr: 0.35`.
- That creates many small wins around +0.7 to +1.7 USD, while a full GBPUSD stop was -9.38 USD.
- One full loss can erase about 6 to 9 recent small winners.

The GBPUSD -9.38 loss was also a quality issue:

- Full-risk GBPUSD BUY 0.07, risk_pct 0.35.
- Hit SL at 1.33638.
- Maintenance postmortem classified it as `weak_trend`.
- Suggested corrective action was `raise_min_adx_or_avoid_range`.
- GBPUSD config allows entry at `adx_min_value: 18`; the trade was below the stricter scale-in ADX threshold of 24.

AUDUSD and USDCAD examples show the other side:

- USDCAD winner split into +1.46 and +1.55 instead of waiting for larger planned TP.
- AUDUSD winners closed at +1.02/+1.74, later +0.70/+0.88.
- The supervisor has mostly logged telemetry and profit-lock behavior; it did not create the GBPUSD loss.

## Risk Interpretation

This is not DANGEROUS because controls are working:

- Control room OK.
- Unknown positions 0.
- Unprotected positions 0.
- Process guard OK.
- Current exposure known and protected.

But it is not promotion-ready:

- Last 50 profit factor is only about 1.15, below the 1.30 gate.
- Last 10 profit factor is below 1.0.
- Current win rate is high, but payoff asymmetry is too weak.

## Recommended Defensive Patch

Apply only after explicit approval because it changes live demo execution behavior:

1. Raise `profit_lock_trigger_rr` from 0.25 to 0.50 or 0.60.
2. Prevent full profit-lock exits before at least 0.50R unless the stop is moved to breakeven.
3. Reduce `risk_pct` and `max_effective_risk_pct` from 0.35 to 0.20-0.25 until profit factor is stable above 1.30.
4. Raise GBPUSD `strategy.adx_min_value` from 18 to at least 22, preferably 24 if sample confirms weak-trend losses continue.
5. Keep current open demo trades under supervisor; do not manually intervene unless risk state changes to DANGEROUS.

