# Aggressive M5 suite change - 2026-05-15

Context: Jean explicitly requested aggressive demo testing across all 12 MT5 bots, with reason/risk controls.

Backup:
- `backup_aggressive_m5_20260515_131155`

Changes applied to 12 active config files used by the existing restart BATs:
- `timeframe: M5` for all 12 bots.
- EMA changed to fast=5 / slow=13.
- `use_retest_filter: false`.
- `use_candle_confirm: false`.
- ADX filter kept enabled, lowered to `adx_min_value: 18`.
- Session filter kept but set to 0-24 for all 12 so no bot is idle just due to session.
- News, spread, trend, equity curve, portfolio/global guards remain enabled.
- Config `execution.trade_enabled` remains false; live-demo execution still requires BAT/CLI `--trade-enabled`.
- Risk reduced versus prior aggressive 12-bot exposure:
  - Majors mostly 0.8%-1.0%
  - Metals 0.7%-0.75%
  - R:R kept 1:2 with tighter M5 SL/TP.

Restart/verification:
- Stopped existing suite with `python WATCHDOG_SAFE_24H.py --stop`.
- Relaunched `_run_all_pro_autorestart.bat`.
- Verified 12 trade loops and 12 restart windows with live-demo mode.
- Logs confirm each bot started as `tf=M5`, `retest=False`, `candle_confirm=False`, `trade_enabled=True`.
- MT5 account 106490890 / MetaQuotes-Demo: positions 0, no deals in first verification window.

Note:
- Even in aggressive M5 mode, the strategy still requires a fresh closed-bar EMA crossover (or ADX-qualified crossover). No immediate market entries are forced.
