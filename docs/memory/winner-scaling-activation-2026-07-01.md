# Winner scaling activation - 2026-07-01

Activation commit already present locally: `6c44ba9` (`chore: activate autonomous winner scaling`).

Risk gate:

- Initial MT5 check before relaunch work: positions=0, orders=0.
- Post-validation MT5 check before relaunch: positions=0, orders=0.
- Post-relaunch MT5 check: positions=0, orders=0, balance=3019.06, equity=3019.06.

Validation:

- `uv run pytest -q`: 105 passed.
- `uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml preflight`: OK for 10 configs.
- `uv run python -m mt5_bot.process_guard`: OK, no duplicate trade configs.

Runtime:

- Watchdog/runner relaunched from a clean MT5 state.
- No manual trade was opened, closed, or modified.
- OpenClaw cron tool was not available in this subagent toolset, so cron cleanup was not performed here.

## Cron activation refresh - 2026-07-01 16:03 America/Lima

The active autonomous configs still carry the conservative winner-scaling
parameters from activation commit `6c44ba9`:

- trigger RR `0.45`, current MFE ratio `0.75`, MAE/MFE cap `0.35`
- add volume ratio `0.50`, add-on risk cap `0.10`
- ADX floor `24`, spread/ATR cap `0.12`
- symbol-specific MFE floors in the 10 configs listed by
  `config/autonomous_agent.yaml`

Risk gate:

- Initial MT5 check before work: positions=0, orders=0.
- Post-validation MT5 check before relaunch: positions=0, orders=0,
  balance=3019.06, equity=3019.06.
- Post-relaunch MT5 check: positions=0, orders=0, balance=3019.06,
  equity=3019.06.

Validation:

- `uv run pytest -q`: 105 passed.
- `uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml preflight`: OK for 10 configs.
- `uv run python -m mt5_bot.process_guard`: OK, no duplicate trade configs.

Runtime:

- Existing watchdog/runner process tree was stopped only after the clean MT5
  gate passed.
- Watchdog/runner relaunched via `MT5_AGENT.bat watchdog-bg`.
- New process tree observed for `mt5_bot.agent_watchdog` and
  `mt5_bot.agent_runner`.
- No manual trade was opened, closed, or modified.
- OpenClaw cron cleanup was attempted by tool discovery, but no cron mutation
  tool was exposed to this subagent.
