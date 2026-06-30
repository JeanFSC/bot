@echo off
cls
echo ===============================================
echo  MT5 AUTONOMOUS AGENT WATCHDOG
echo  Supervisa, reinicia y reporta salud cada 15 min
echo ===============================================
echo.
echo [INFO] Esto inicia el watchdog, y el watchdog inicia el agente.
echo [INFO] Presiona Ctrl+C para detener watchdog + agente hijo.
echo [INFO] Reportes: data\watchdog_health.jsonl
echo.
pause
cd /d "%~dp0"
uv run python -m mt5_bot.agent_watchdog --agent-config config/autonomous_agent.yaml --interval-seconds 900 --stale-after-seconds 1200 --report-path data/watchdog_health.jsonl
pause
