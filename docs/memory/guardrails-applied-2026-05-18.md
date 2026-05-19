# Guardrails Applied - 2026-05-18

Scope: implemented Jean-approved risk guardrails after trade-day audit. Suite remained stopped; no orders were opened, closed, modified, or restarted.

## Code Changes

- Added persistent daily start equity lookup from account snapshots so daily loss cap survives bot restarts during the same UTC day.
- Added hard symbol loss-streak guard: new entries are blocked when consecutive losing exits reach `max_symbol_consecutive_losses`.
- Added hard same-direction theme overlap guard: correlated positions in the same direction can block new entries via `max_same_direction_theme_positions`.
- Initialized adaptive cooldown safely to avoid an unbound variable when there are zero consecutive losses.
- Added tests for same-direction theme blocking.

## Suite Config Changes

Applied to `config/pro*.yaml`:

- `max_daily_loss_pct: 1.5`
- `max_consecutive_losses: 1`
- `max_symbol_consecutive_losses: 1`
- `max_same_direction_theme_positions: 1`
- `partial_close_ratio: 0.35`

EURUSD-specific reduction because it caused the largest drawdown:

- `config/pro.yaml`: `risk_pct: 0.35`, `max_effective_risk_pct: 0.35`, `max_symbol_daily_loss_pct: 0.35`
- `config/pro_eurusd_m5_aggressive.yaml`: same reduced caps.

## Verification

- Config load for all `pro*.yaml`: PASS
- Targeted tests: `13 passed`
- Full tests: `31 passed`
- Suite status after changes: `trade_loops=0`, `restart_windows=0`, `open_positions=0`, `recent_log_errors=0`

## Operational Note

Do not restart suite until Jean explicitly confirms. If restarted, use the controlled launcher path, not ad hoc process starts.

