# Suite Loss Analysis From 2026-05-15

## Correction

Jean clarified that the valid audit window starts on 2026-05-15 because prior trades belonged to versions with known issues that were fixed during the process. This report supersedes any conclusions that used earlier trades as part of the current-suite assessment.

This is operational/trading-system analysis, not financial advice.

## Evidence

- Source of truth: MetaTrader 5 history filtered by current suite magic numbers.
- Period: 2026-05-15 00:00 UTC through 2026-05-19 audit time.
- Suite state after Jean request: stopped and verified stopped.

## Corrected Headline

- Total deals in period: 62.
- Entry deals: 25.
- Closed PnL deals: 37.
- Total closed PnL since 2026-05-15: +8,293.29 USD.

Daily PnL:

- 2026-05-15: +1,031.09
- 2026-05-17: +9,088.95
- 2026-05-18: -1,489.42
- 2026-05-19: -337.33

Interpretation: the corrected post-fix period is net profitable, but losses on 2026-05-18 and 2026-05-19 expose which bots/rules need tightening before a restart or VPS migration.

## Ranking Since 2026-05-15

| Bot | Entries | Closed | W/L | PnL | PF | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| XAUUSD | 1 | 2 | 2/0 | +10,582.05 | n/a | Best PnL, but gold remains high-risk by nature |
| USDCHF | 4 | 7 | 6/1 | +1,563.62 | 3.00 | Best quality candidate |
| GBPJPY | 5 | 8 | 7/1 | +6.38 | 4.71 | Stable but tiny contribution |
| USDJPY | 2 | 3 | 2/1 | -3.37 | 0.22 | Flat/negative in this window |
| USDJPY_ASIA | 1 | 1 | 0/1 | -3.66 | 0.00 | Tiny loss |
| NZDUSD | 2 | 3 | 2/1 | -395.04 | 0.42 | Win rate positive, expectancy negative |
| GBPUSD | 5 | 8 | 6/2 | -433.80 | 0.68 | Win rate positive, expectancy negative |
| USDCAD | 1 | 1 | 0/1 | -482.42 | 0.00 | One failed entry |
| XAUUSD_M5 | 1 | 1 | 0/1 | -603.84 | 0.00 | Failed in this period |
| EURUSD | 3 | 3 | 0/3 | -1,936.63 | 0.00 | Worst post-fix bot |

## Loss Drivers In Valid Window

Worst losses:

- USDCHF 2026-05-19 08:48 Lima: -781.48, SL, 15.01 lots.
- EURUSD 2026-05-18 21:17 Lima: -752.22, SL, 13.93 lots.
- EURUSD 2026-05-18 12:03 Lima: -722.40, SL, 9.03 lots.
- GBPUSD 2026-05-19 04:33 Lima: -677.37, SL, 10.11 lots.
- NZDUSD 2026-05-19 08:47 Lima: -676.80, SL, 14.40 lots.
- GBPUSD 2026-05-18 12:03 Lima: -659.00, SL, 6.59 lots.
- XAUUSD_M5 2026-05-18 14:49 Lima: -603.84, SL, 0.51 lots.
- USDCAD 2026-05-19 05:16 Lima: -482.42, SL, 18.42 lots.
- EURUSD 2026-05-15 18:32 Lima: -462.01, SL, 9.83 lots.

## Diagnosis

1. The corrected suite is net profitable, mostly due XAUUSD and USDCHF.
2. EURUSD is the clear post-fix failure: 3 trades, 3 losses, -1,936.63.
3. GBPUSD and NZDUSD had positive win rates but negative PnL, meaning partial wins are too small relative to full SL losses.
4. Lot sizes are still aggressive enough that one full SL costs roughly 0.5%-0.9% of equity on several FX bots.
5. XAUUSD_M5 is not justified by this window: one entry, one SL.
6. USDCHF is the strongest candidate, but its one loss was still large enough to require risk scaling.
7. Gold M15 had the largest positive contribution; do not treat it as safe, but do not discard it based on pre-15 losses.

## Restart Plan

Do not restart the whole suite at once. Use staged re-enable:

Phase 1:

- Fix runtime errors, especially `timedelta` crash loops.
- Use magic-scoped report as official PnL.
- Add 2-hour report status: OK / DEGRADED / DANGEROUS / DOWN.

Phase 2, limited forward run:

- Enable USDCHF first at reduced risk.
- Enable XAUUSD M15 only with stricter hard-loss cap and smaller max risk.
- Enable GBPJPY only if operationally useful, because its PnL is currently negligible.

Keep disabled initially:

- EURUSD: failed 3/3, worst valid-window bot.
- GBPUSD: negative expectancy despite win rate.
- NZDUSD: negative expectancy despite win rate.
- USDCAD: insufficient and negative.
- XAUUSD_M5: failed in this window.
- USDJPY and USDJPY_ASIA: too close to flat/negative.

Risk gates:

- Max projected loss per trade: 0.25%-0.35% during test.
- Max daily loss global: 1.0%.
- Max daily loss per bot: 0.5%.
- Pause bot after 2 full SL losses in valid window.
- Require at least 30 post-fix trades before declaring a bot good.

## Corrected Verdict

From 2026-05-15 onward, the suite was profitable but uneven. The plan should not be to abandon it; the plan should be to preserve the profitable pockets, cut the negative-expectancy bots, reduce sizing, and harden reporting/runtime before restart or VPS migration.

