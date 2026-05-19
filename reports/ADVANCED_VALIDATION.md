# Advanced Validation Report

Generated: `2026-05-16T04:27:58.435805+00:00`

## Group validation

| Group | Trades | PnL | PF | Exp | DD | MC | Walk-forward | Status |
|---|---:|---:|---:|---:|---:|---|---|---|
| fx_majors | 194 | -1102.65 | 0.40 | -5.68 | 1110.65 | ok | ok | WAITING_OR_FAIL |
| jpy_crosses | 4 | 3160.70 | INF | 790.17 | 0.00 | insufficient_sample | insufficient_sample | WAITING_OR_FAIL |
| metals | 5 | -34992.54 | 0.00 | -6998.51 | 34992.54 | insufficient_sample | insufficient_sample | WAITING_OR_FAIL |

## Symbol validation

| Symbol | Trades | PnL | PF | Exp | DD | Status |
|---|---:|---:|---:|---:|---:|---|
| AUDUSD | 2 | -929.15 | 0.00 | -464.57 | 929.15 | WAITING_OR_FAIL |
| EURUSD | 188 | -132.00 | 0.84 | -0.70 | 360.00 | WAITING_OR_FAIL |
| GBPUSD | 4 | -41.50 | 0.16 | -10.38 | 49.50 | WAITING_OR_FAIL |
| USDJPY | 4 | 3160.70 | INF | 790.17 | 0.00 | WAITING_OR_FAIL |
| XAUUSD | 5 | -34992.54 | 0.00 | -6998.51 | 34992.54 | WAITING_OR_FAIL |

## Gate

Advanced validation is functional, but most outputs will remain `insufficient_sample` until enough clean post-fix trades exist.
