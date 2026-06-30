@echo off
cd /d "%~dp0"
echo WARNING: Esto habilita operaciones en cuenta DEMO si config/autonomous_agent.yaml tiene mode: demo.
echo Verifica preflight antes de continuar.
pause
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml run-once --allow-demo-orders
pause
