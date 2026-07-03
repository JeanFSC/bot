# Control Room Chaos Test - 2026-07-03 13:41 UTC

## Scope

Verify that new entries are blocked when the live-position supervisor becomes stale.

No trades, strategy configs, SL/TP, or risk parameters were modified.

## Precheck

- `CONTROL_ROOM OK`
- positions `0/0`
- unknown positions `0`
- unprotected positions `0`
- supervisor mode `demo_actions_enabled`
- heat decision `allow_new_entries`

## Action

Stopped the `supervisor-demo-bg` process chain only:

- `cmd.exe /c MT5_AGENT.bat supervisor-demo-bg`
- `uv run python -u -m mt5_bot.live_position_supervisor run-continuous ...`
- child Python supervisor processes

Waited 35 seconds.

## Expected Result

`CONTROL_ROOM` should degrade to WARN/CRITICAL and active trade loops should record `pretrade_block=control_room_not_ok` instead of opening new orders.

## Observed Result

`CONTROL_ROOM WARN`

- reason: `supervisor_report_stale`
- supervisor age: `39s`
- heat age: `5s`
- positions `0/0`
- process guard OK

Runtime evidence:

- `data/pro_gbp_m5.sqlite` recorded repeated `runtime_events`:
  - `event_type=pretrade_block`
  - `reason=control_room_not_ok`
  - context reasons: `["supervisor_report_stale"]`

Order evidence:

- No successful `orders.phase='send' AND retcode=10009` rows appeared after the chaos-test start timestamp `2026-07-03T13:39:35Z`.

## Recovery

Restarted `MT5_AGENT.bat supervisor-demo-bg`.

Final state:

- `CONTROL_ROOM OK`
- supervisor age `2s`
- heat age `7s`
- positions `0/0`
- supervisor mode `demo_actions_enabled`
- policy `portfolio_heat_allows_actions`

## Verdict

PASS. The control-room entry gate blocked new entries while supervisor reporting was stale, and supervisor recovery restored `CONTROL_ROOM OK`.
