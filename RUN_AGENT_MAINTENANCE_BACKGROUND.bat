@echo off
REM Runs maintenance once without pause prompts. Safe for Task Scheduler.

cd /d "%~dp0"
if not exist logs mkdir logs
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

uv run python -m mt5_bot.maintenance --agent-config config/autonomous_agent.yaml --reports-dir reports --backups-dir backups --backup-keep 48 --notify >> logs\agent_maintenance.out.log 2>> logs\agent_maintenance.err.log
