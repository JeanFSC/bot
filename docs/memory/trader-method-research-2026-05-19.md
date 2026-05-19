# Trader method research - 2026-05-19

Jean requested a /goal to deeply research Fabio Valentini and Patrick Nill, then restructure paused MT5 bots.

Evidence found:

- Fabio Valentini: public sources support an Auction Market Theory / Volume Profile / VWAP / Order Flow scalping playbook, mainly futures/NQ during liquid sessions. Key implementation idea is market state -> location -> aggression confirmation, not generic EMA crossover.
- Patrick Nill: exact identity/methodology not verified from public search. Do not invent attribution. Ask Jean for a link/handle/correct spelling before encoding rules under that name.

Implementation done:

- Added docs/GOAL_TRADER_METHOD_RESEARCH.md.
- Added src/mt5_bot/market_structure.py with anchored_vwap, volume_profile, classify_market_state.
- Added tests/test_market_structure.py.
- Tests passed: 35 passed.

Operating decision:

- Keep reduced live mode separate: USDCHF, XAUUSD main, GBPJPY.
- Keep paused bots paused until redesigned candidates pass backtest and forward-test gates.
- Fabio-style methods require a new research/backtest layer because MT5 forex data lacks true footprint/CVD; use tick-volume/candle/VWAP/profile proxies and label them as proxies.
