# Suite checkpoint - 2026-05-17

Context: Jean asked Bobby to review the MT5 suite, verify the recent trade that could not be cancelled before market close, run QA/status checks, and consider launching the suite again.

## Read-only checks run

- `python WATCHDOG_SAFE_24H.py --mode live-demo --status --expect-running`
- `python qa_suite_smoke.py`
- `python WATCHDOG_SAFE_24H.py --mode live-demo --preflight`
- `python -m pytest -q`
- Read-only MT5 history query through `MetaTrader5.history_deals_get/history_orders_get`
- `python scripts/forward_report.py --help` (script prints report despite --help)

## Current MT5 status

- Account: `106490890 / MetaQuotes-Demo`
- Balance/equity observed: `91449.18 / 91449.18`
- Open positions observed from MT5: `0`
- Suite processes: `0` trade loops, `0` restart windows
- Watchdog/status reported one watchdog process

## QA results

- `qa_suite_smoke.py`: PASS
  - 12 configs loaded.
  - 12-symbol launcher present.
  - MT5 check passed for all 12 symbols.
- `WATCHDOG_SAFE_24H.py --mode live-demo --preflight`: PASS
  - `PREFLIGHT_OK mode=live-demo safe configs, 12-bot launcher present`
- `python -m pytest -q`: PASS
  - `28 passed`
- `qa_full_mt5.py`: FAIL / obsolete assertion
  - Fails at `assert c.max_portfolio_open_positions == 5` for `config/pro.yaml`.
  - Current configs use `max_portfolio_open_positions: 3`, consistent with newer tighter guardrails.

## Recent trade verification

Position: `8661985181`
Symbol: `XAUUSD`
Magic: `260436`
Direction: SELL

Deals:

- 2026-05-15T21:36:24Z: opened SELL `7.90` lots at `4555.97`, SL `4563.62`, TP `4540.46`
- 2026-05-15T22:10:16Z: partial close `3.95` lots at `4552.19`, profit `+1493.10`
- 2026-05-18T01:01:30Z: final close `3.95` lots at `4532.96`, profit `+9088.95`, swap `-18.17`, comment `[tp 4540.46]`

Net position result: approximately `+10563.88`.

## Risk interpretation

Outcome was very good, but this trade should not be treated as clean proof that the strategy is safe.

Reason:

- Prior note `improvements-forward-test-2026-05-15.md` says the XAUUSD `7.90` lot position was oversized due to MetaQuotes demo underreporting XAU/XAG tick value.
- The sizing fix was applied after the oversized legacy position was already open.
- Future metals positions should be materially smaller, around `0.8` lots for similar risk/SL according to the prior note.
- The original XAUUSD SL distance was about `7.65` price units, so the pre-fix position carried several thousand dollars of theoretical risk.

Conclusion: good realized demo trade, but not yet a green light to scale. Treat it as lucky/good outcome from an oversized legacy trade plus valid TP behavior.

## Journal inconsistency

`scripts/forward_report.py` still showed local SQLite open-position state even though MT5 reported `open_positions=0`:

- `pro.sqlite`: open=1, floating=-353.88
- `pro_gold.sqlite`: open=1, floating=3926.30

This suggests DB/journal reconciliation is incomplete or stale after position closure. Before relying on reports, add/verify reconciliation from MT5 live/history to SQLite state.

## Launch decision

Bobby did not start `START_LIVE_DEMO_24H.bat` or `_run_all_pro_autorestart.bat` because they launch 12 bots with `--trade-enabled`. Even in demo mode this can place live demo orders, so it requires explicit Jean confirmation after the risk summary.

Recommended confirmation phrase:

`ARRANCA SUITE DEMO 12 BOTS`

If confirmed, run:

`START_LIVE_DEMO_24H.bat`

Then verify:

`python WATCHDOG_SAFE_24H.py --mode live-demo --status --expect-running`

Expected: 12 trade loops, 12 restart windows, demo account, and no unsafe real-account mismatch.

## Launch update - 2026-05-17 23:11 America/Lima

Jean explicitly asked to start the suite: "arranca la suite, que siga haciendo trades..."

Action taken:

- Started `START_LIVE_DEMO_24H.bat`.
- Verified after startup:
  - `trade_loops=12`
  - `restart_windows=12`
  - `--trade-enabled` active in live-demo mode
  - account `106490890 / MetaQuotes-Demo`
  - balance/equity `91449.18 / 91449.18`
  - open positions `0`
- Verified again ~35 seconds later:
  - `trade_loops=12`
  - `restart_windows=12`
  - open positions `0`

Initial forward report:

- New journal rows are being written across the 12 DBs.
- Sent/orders: `0` so far.
- Main reason: `no_closed_bar_crossover`.
- Local SQLite still shows stale open states for `pro.sqlite` and `pro_gold.sqlite` even though MT5 live status says `open_positions=0`; reconciliation remains TODO.
