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
call MT5_AGENT.bat watchdog
pause
