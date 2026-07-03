# MT5 Experiment Contamination Audit - 2026-07-03 13:32 UTC

## Scope

Audit requested after Claude review of commits `538f4c0`, `7c7cbe1`, and the supervisor activation record. Goal: decide whether the active 50-trade post-baseline experiment is measuring clean post-patch behavior or includes trades opened while sidecars were stale.

No trades, configs, SL/TP, or risk parameters were modified.

## Sidecar Gaps

Detected report gaps:

- `data/live_position_supervisor.jsonl`: `2026-07-03T07:53:25Z -> 2026-07-03T10:33:47Z` (`9622s`) exceeded the 20s supervisor freshness threshold.
- `data/live_position_supervisor.jsonl`: `2026-07-03T12:28:28Z -> 2026-07-03T13:01:34Z` (`1986s`) exceeded the 20s supervisor freshness threshold.
- `data/portfolio_heat.jsonl`: `2026-07-03T12:31:45Z -> 2026-07-03T13:01:32Z` (`1787s`) exceeded the 60s heat freshness threshold.

## Executed Orders During Gaps

- `GBPJPY` order send in `data/pro_gbpjpy.sqlite`
  - local order timestamp: `2026-07-03T07:55:55.651110Z`
  - order/deal: order `9414675477`, opening deal `9081085058`
  - side/volume: sell `0.01`
  - open price: `215.031`
  - SL/TP requested: `215.192` / `214.698`
  - gap overlap: inside `supervisor_report_stale` window `2026-07-03T07:53:25Z -> 2026-07-03T10:33:47Z`
  - close: ticket `9082174691`, broker comment `[sl 215.192]`, PnL `-1.00`

No executed send orders were found during the second stale window (`2026-07-03T12:28:28Z -> 2026-07-03T13:01:34Z`).

## Verdict

The first post-baseline GBPJPY loss is real account history, but it is not a clean experiment sample because the position was opened while the live-position supervisor was stale.

Use two counters from here:

- Raw post-baseline: `1/50`, includes GBPJPY `9082174691`, PF `0.00`, expectancy `-1.00`.
- Clean post-restoration experiment: `0/50`, clean baseline reset to exclude contaminated GBPJPY.

Operational rule: do not evaluate the patch by the contaminated GBPJPY trade. Restart the clean 50-trade count from the period after supervisor/heat restoration and keep the raw history visible for audit.

## Fix Status

- Implemented in the same hardening block: entry loop blocks new entries when `CONTROL_ROOM != OK`.
- Implemented in the same hardening block: MT5 initialization uses a process mutex plus retry backoff/jitter to avoid `Authorization failed (-6)` crash loops from concurrent initializations.
- Left unchanged: exit parameters from `538f4c0`; do not change exits again until there is enough clean sample.
