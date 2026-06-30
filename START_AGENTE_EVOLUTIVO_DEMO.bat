@echo off
cls
echo ===============================================
echo  AGENTE AUTONOMO EVOLUTIVO M5 - MODO DEMO
echo  Bucle continuo. Aprende de cada resultado.
echo  Kill switch: detente automatico si equity ^< 2900
echo ===============================================
echo.
echo [INFO] Presiona Ctrl+C para detener manualmente.
echo [INFO] El agente se reinicia automatico tras cada ciclo.
echo [INFO] Monitorea: data/autonomous_agent_memory.sqlite
echo.
pause
cd /d "%~dp0"

:RESTART
cls
echo [%DATE% %TIME%] === Iniciando ciclo continuo ===
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml run-continuous

echo.
echo [WARN] Bot salio con error. Verifica MT5 y equity.
echo [INFO] Reiniciando en 10 segundos... Presiona Ctrl+C para detener.
timeout /t 10 /nobreak >nul
goto RESTART
