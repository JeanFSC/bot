# Forward Test /goal

Generated: `2026-05-16T04:28:01.068131+00:00`

## Phase checklist

- [ ] Review latest AUDIT_TOTAL_STRATEGY and identify weak bots
- [ ] Resolve/segregate the pre-fix XAUUSD open position before clean validation
- [ ] Run 12-bot forward test from CONTROL_BOTS only, no direct 12-window launcher
- [ ] Generate daily_report + audit_total_strategy + suite_goal after each trading day
- [ ] Keep risk capped until clean sample passes PF/expectancy/drawdown gates
- [ ] Add/execute walk-forward, Monte Carlo, and bot ranking before risk escalation

## Current gates

- [x] `suite_stopped_for_audit` - {'trade_loops': 0, 'restart_wrappers': 0, 'controllers': 2}
- [x] `reports_exist` - audit + goal reports
- [x] `controller_workflow_required` - CONTROL_BOTS.bat present
- [ ] `legacy_xau_position_handled` - open_positions=[{'ticket': 8661985181, 'symbol': 'XAUUSD', 'type': 1, 'volume': 3.95, 'price_open': 4555.97, 'sl': 4555.79, 'tp': 4540.46, 'profit': 3926.3, 'magic': 260436}]
- [ ] `validation_sample_gate` - requires 20-50 clean post-fix trades per active bot/group

Preflight hard gate: **BLOCKED**
Validation gate: **WAITING ON CLEAN SAMPLE**

## Latest audit summary

Suite score active 12: **8.46/10**
| XAUUSD `pro_gold.yaml` | M5 | 8.00 | 2 | -17414.97 | 0.00 | -8707.49 | 17414.97 | insufficient_clean_trade_sample, too_few_realized_trades, slippage_large_vs_sl |
| AUDUSD `pro_aud.yaml` | M5 | 8.50 | 2 | -929.15 | 0.00 | -464.57 | 929.15 | insufficient_clean_trade_sample, too_few_realized_trades |
| GBPUSD `pro_gbp.yaml` | M5 | 8.50 | 4 | -41.50 | 0.16 | -10.38 | 49.50 | insufficient_clean_trade_sample, too_few_realized_trades |
| USDJPY `pro_jpy.yaml` | M5 | 8.50 | 3 | 3160.70 | INF | 1053.57 | 0.00 | insufficient_clean_trade_sample, too_few_realized_trades |
| USDJPY `pro_jpy_asia.yaml` | M5 | 8.50 | 0 | 0.00 | n/a | n/a | 0.00 | insufficient_clean_trade_sample, too_few_realized_trades |
| XAUUSD `pro_gold_m5.yaml` | M5 | 8.50 | 2 | -162.60 | 0.00 | -81.30 | 162.60 | insufficient_clean_trade_sample, too_few_realized_trades |

## Operator rule

Start only from `CONTROL_BOTS.bat` after Jean explicitly approves forward-test restart.

## 2026-05-16 operator decision

Jean delegated the legacy XAUUSD handling decision to Bobby.

Decision:

- Treat ticket `8661985181` XAUUSD SELL `3.95` lots as contaminated pre-fix exposure.
- Do not include it in clean post-fix validation under any circumstance.
- Keep the suite stopped while the market is closed.
- On the next weekday/market session, first re-check live status, spread, SL/TP, floating PnL, and logs.
- Preferred risk-first action if the position is still open and market conditions are executable: close or otherwise isolate the legacy position before restarting forward-test validation.
- Restart the 12-bot suite only from `CONTROL_BOTS.bat` after the legacy exposure is handled/segregated and the preflight gate is regenerated.

Execution caveat:

- Bobby must not send a close/modify order without a fresh explicit confirmation at execution time, because it is a live/demo trading action.
