@echo off
REM Starts the MT5 autonomous watchdog without pause prompts.
REM Use for scheduled tasks, NSSM, or a hidden background PowerShell launch.

cd /d "%~dp0"
if not exist logs mkdir logs
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

uv run python -u -m mt5_bot.agent_watchdog --agent-config config/autonomous_agent.yaml --interval-seconds 900 --stale-after-seconds 3600 --report-path data\watchdog_health.jsonl >> logs\agent_watchdog_service.out.log 2>> logs\agent_watchdog_service.err.log
