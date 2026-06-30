@echo off
REM Instala tarea programada local/VPS para mantenimiento cada hora.
REM Ejecutar como Administrador en el VPS si quieres que corra sin sesion interactiva.

set TASK_NAME=MT5AgentMaintenanceHourly
set BOT_DIR=%~dp0

schtasks /Create /TN %TASK_NAME% /SC HOURLY /MO 1 /TR "cmd /c cd /d \"%BOT_DIR%\" && uv run python -m mt5_bot.maintenance --agent-config config/autonomous_agent.yaml --reports-dir reports --backups-dir backups --backup-keep 48" /F

echo Tarea creada: %TASK_NAME%
pause
