# AUDIT_TOTAL_STRATEGY

Generated: `2026-05-19T17:46:03.626820+00:00`

Suite score active 12: **8.38/10**

## Active bot scores

| Bot | TF | Score | Trades | PnL | PF | Exp | DD | Key blockers |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| GBPUSD `pro_gbp.yaml` | M5 | 7.00 | 17 | -475.94 | 0.66 | -28.00 | 700.50 | insufficient_clean_trade_sample, profit_factor_below_validation_threshold, non_positive_expectancy |
| NZDUSD `pro_nzdusd.yaml` | M5 | 7.00 | 5 | -395.04 | 0.42 | -79.01 | 676.80 | insufficient_clean_trade_sample, profit_factor_below_validation_threshold, non_positive_expectancy |
| AUDUSD `pro_aud.yaml` | M5 | 8.50 | 2 | -929.15 | 0.00 | -464.57 | 929.15 | insufficient_clean_trade_sample, too_few_realized_trades |
| EURUSD `pro.yaml` | M5 | 8.50 | 4 | -1474.62 | 0.00 | -368.65 | 1474.62 | insufficient_clean_trade_sample, too_few_realized_trades |
| USDCAD `pro_usdcad.yaml` | M5 | 8.50 | 2 | -482.42 | 0.00 | -241.21 | 482.42 | insufficient_clean_trade_sample, too_few_realized_trades |
| USDJPY `pro_jpy_asia.yaml` | M5 | 8.50 | 2 | -3.66 | 0.00 | -1.83 | 3.66 | insufficient_clean_trade_sample, too_few_realized_trades |
| XAGUSD `pro_silver.yaml` | M5 | 8.50 | 0 | 0.00 | n/a | n/a | 0.00 | insufficient_clean_trade_sample, too_few_realized_trades |
| XAUUSD `pro_gold.yaml` | M5 | 8.50 | 3 | -8344.19 | 0.52 | -2781.40 | 17414.97 | insufficient_clean_trade_sample, too_few_realized_trades |
| XAUUSD `pro_gold_m5.yaml` | M5 | 8.50 | 4 | -766.44 | 0.00 | -191.61 | 766.44 | insufficient_clean_trade_sample, too_few_realized_trades |
| GBPJPY `pro_gbpjpy.yaml` | M5 | 9.00 | 13 | 6.39 | 4.74 | 0.49 | 1.71 | insufficient_clean_trade_sample |
| USDCHF `pro_usdchf.yaml` | M5 | 9.00 | 11 | 1563.62 | 3.00 | 142.15 | 781.48 | insufficient_clean_trade_sample |
| USDJPY `pro_jpy.yaml` | M5 | 9.00 | 8 | 3157.33 | 733.56 | 394.67 | 4.31 | insufficient_clean_trade_sample |

## Non-active configs found

- `config\pro_eurusd_m5_aggressive.yaml` (EURUSD) — not in active 12 launcher
- `config\pro_gbp_m5_aggressive.yaml` (GBPUSD) — not in active 12 launcher
- `config\pro_jpy_m5_aggressive.yaml` (USDJPY) — not in active 12 launcher

## 10/10 checklist gate

- [ ] Minimum 20–50 clean post-fix trades per active bot/group
- [ ] Active suite score >= 9.0 for risk/execution/reporting before scaling
- [ ] Profit factor >= 1.3 and positive expectancy on out-of-sample / forward sample
- [ ] Metals results reported separately from FX majors
- [ ] No open contaminated position mixed into clean validation
- [ ] No duplicated trade loops or visible terminal sprawl; use controller workflow
