# MT5 Supervisor Action Schema Audit - 2026-07-02

## Verdict

Status: `IMPLEMENTED_SAFE_SCHEMA_NOT_ACTIVATED`

The action-enabled supervisor should not be treated as another entry bot. It
must be a position manager that only touches positions already owned by the
active config map `(symbol, magic)`, and it must be subordinated to fresh
portfolio heat and process/control-room checks.

## Intended Interaction Model

1. Entry agent searches for new trades.
2. Portfolio heat agent computes current account/book risk.
3. Supervisor manages existing owned positions only.
4. Control room reconciles freshness, process uniqueness, heat, watchdog, and
   supervisor action state.

The supervisor must never:

- scan for new entries;
- own unknown positions;
- run duplicated beside another supervisor;
- add risk when portfolio heat is stale, blocking, or reducing;
- repeat one-shot actions after process restart.

## Action Classes

Allowed after explicit action-mode activation and fresh heat:

- telemetry and MFE/MAE metrics;
- early no-favorable-excursion exits;
- time stops;
- profit-lock exits;
- partial closes;
- trailing-stop SL updates.

Allowed only when portfolio heat explicitly allows adding risk:

- winner scale-in/add-on.

Blocked:

- any action when heat is missing or stale;
- any action when unknown positions exist;
- add-on risk when heat says block or reduce/wait;
- repeated partial close or repeated scale-in on the same ticket.

## Bugs/Risks Found

- `supervisor-demo-bg` used a separate report path, so the default control-room
  snapshot could keep reading the read-only report and hide the action-mode
  state.
- The supervisor creates a fresh executor per config/cycle. Executor
  `_partial_closed_tickets` was only in-memory, so an action supervisor could
  partial-close the same ticket again after the next cycle/restart.
- Winner scale-in recorded its runtime event immediately after `order_send`,
  even if the send retcode failed. That could falsely block a later valid
  add-on attempt.
- Action-enabled supervisor had no portfolio-heat freshness policy before
  running management actions.

## Implemented Fixes

- Added `ActionPolicy` to `live_position_supervisor`.
- Action mode now requires fresh `data/portfolio_heat.jsonl`.
- Risk-management actions are blocked if heat is missing/stale or unknown
  positions exist.
- Winner scale-in runs only when heat decision is `allow_new_entries`.
- Action supervisor reports now include:
  - `action_mode`;
  - `action_policy`.
- `supervisor-demo-bg` now writes to the same control-room supervisor report
  path: `data\live_position_supervisor.jsonl`.
- Control room now renders supervisor mode/policy and warns if an action-enabled
  supervisor is running with a blocking policy.
- Partial close now uses persistent `runtime_events` as a one-shot ticket
  ledger.
- Winner scale-in now records its one-shot event only after successful send
  retcode.

## Activation Rule

Do not start `supervisor-demo-bg` unless Jean explicitly approves action mode.

Before activation:

```powershell
cmd /c MT5_AGENT.bat control-room
cmd /c MT5_AGENT.bat preflight
cmd /c MT5_AGENT.bat process-guard
```

Required state:

- control room `OK`;
- no duplicate supervisor;
- portfolio heat fresh;
- unknown positions `0`;
- unprotected positions `0`;
- Jean explicitly approves action-mode activation.

## Current Boundary

No manual trade was opened, closed, modified, or scaled during this audit.
The read-only supervisor and portfolio heat monitors remain the active safe
state.

