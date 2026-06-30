@echo off
cd /d "%~dp0"
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml preflight
pause
