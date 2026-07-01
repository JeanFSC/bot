# Autonomous Demo Active Profile - 2026-06-30

## Decision

Jean asked to make the demo agent more active and stop using very small
orders on a 3000 USD demo balance. The agent remains demo-only, but the active
profile now scans more markets, rotates faster, and uses larger per-trade risk.

## Evidence Checked

- MT5 account was connected and demo trading was allowed.
- No open positions or pending orders before relaunch.
- `uv run pytest -q`: 94 passed.
- `MT5_AGENT.bat preflight`: OK for all active configs.
- `MT5_AGENT.bat process-guard`: OK.
- Quick replay over 1500 recent M5 bars:
  - USDCHF: 27 trades, 48.1% win rate, +7.70 net pips.
  - GBPJPY: 23 trades, 34.8% win rate, +128.50 net pips.
  - EURUSD aggressive: 63 trades, 36.5% win rate, +5.30 net pips.
  - GBPUSD aggressive: 36 trades, 33.3% win rate, +6.60 net pips.
  - USDCAD: 34 trades, 47.1% win rate, +29.60 net pips.
  - XAUUSD: 27 trades, 29.6% win rate, -1146.00 net pips.
  - USDJPY aggressive: 53 trades, 30.2% win rate, -31.50 net pips.
  - AUDUSD: 55 trades, 25.5% win rate, -131.30 net pips.
  - NZDUSD: 55 trades, 36.4% win rate, -44.80 net pips.

The long multi-symbol replay via date range timed out against MT5, so the
decision used the faster recent-bar replay plus live preflight checks.

## Changes

- `config/autonomous_agent.yaml`
  - `max_seconds`: 900 -> 300.
  - `poll_seconds`: 15 -> 10.
  - Active configs increased from 3 to 6:
    - `config/pro_usdchf.yaml`
    - `config/pro_gbpjpy.yaml`
    - `config/pro_eurusd_m5_aggressive.yaml`
    - `config/pro_gbp_m5_aggressive.yaml`
    - `config/pro_usdcad.yaml`
    - `config/pro_gold.yaml`
  - `reduced_risk_pct`: 0.05 -> 0.35.

- USDCHF and GBPJPY:
  - `risk_pct`: 0.05 -> 0.35.
  - `max_effective_risk_pct`: 0.05 -> 0.35.
  - ADX gate loosened to 18.
  - RSI bounds widened to 72/28.

- GBPUSD aggressive and USDCAD:
  - normalized active risk to 0.35 and cap to 0.35.
  - USDCAD `baseline_equity`: 102000 -> 3000.

- XAUUSD:
  - kept active for metal exposure, but lower risk due weak quick replay.
  - `risk_pct`: 0.05 -> 0.20.
  - `max_effective_risk_pct`: 0.05 -> 0.20.
  - ADX gate loosened to 20.

## Runtime

The watchdog was relaunched after confirming no positions/orders. New active
trade command observed:

```text
mt5_bot trade --config config\pro_usdchf.yaml --max-seconds 300 --poll-seconds 10 --floor-equity 2900.0 --trade-enabled
```

The first new cycle started on USDCHF. Temporary `journal_missing` warnings for
newly added symbols are expected until each new DB/journal is created during the
first full rotation.

## Guardrails Kept

- `demo_only: true`
- MT5 permission checks.
- news filter.
- floor equity: 2900.
- per-symbol daily/weekly loss caps.
- process duplicate guard.
- portfolio exposure guard.
- no manual forced orders.

## Profit Protection Follow-Up

Jean challenged the first larger USDCHF demo order because it moved toward TP
but later closed by SL. Broker history showed it did not touch TP, but the
incident exposed two real weaknesses:

- the ATR-derived stop could become too small for a larger demo lot;
- open-position management was mostly trailing/partial close, not a direct
  "take profit before the move fades" exit.

Changes added after that incident:

- `min_effective_sl_pips` prevents microscopic SL distances when risk is
  increased. If ATR produces a smaller SL, the order uses the configured floor
  and resizes volume from that wider SL.
- `profit_lock_enabled` closes a profitable open position when it has already
  reached enough MFE and then gives back too much of that MFE before TP.
- Active configs now enable profit lock and minimum SL floors:
  - forex majors: 8 pips minimum SL;
  - GBPJPY: 12 pips minimum SL;
  - XAUUSD: 180 pips minimum SL.

This keeps the demo agent more active, but makes it less likely to repeat the
USDCHF pattern: big lot, tiny stop, no active profit exit.

## Winner Scaling Activation - 2026-07-01

After commit `598d710` staged the executor support, winner scaling was enabled
only for the active autonomous demo configs in `config/autonomous_agent.yaml`.
The activation uses conservative add-on gates:

- trigger RR: 0.45
- current MFE ratio: 0.75
- max MAE/MFE ratio: 0.35
- add volume ratio: 0.50
- max add-on risk: 0.10%
- minimum ADX: 24
- max spread/ATR ratio: 0.12

Minimum MFE is matched to the active symbol profile: 2 pips for major FX pairs,
4 pips for USDJPY, 5 pips for GBPJPY, 60 pips for XAUUSD, and 8 pips for
XAGUSD. This keeps the feature focused on confirmed winners while preserving
the existing demo-only, floor-equity, news, exposure, and duplicate-process
guardrails.
