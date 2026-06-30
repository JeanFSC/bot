@echo off
REM Runs a 30-day replay/backtest report for the autonomous agent configs.

cd /d "%~dp0"
if not exist reports mkdir reports
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

uv run python -m mt5_bot.replay --agent-config config/autonomous_agent.yaml --days 30 --out-dir reports --name replay_30d
pause
