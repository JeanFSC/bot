@echo off
REM Instala tarea programada local/VPS para mantenimiento cada hora.
REM Ejecutar como Administrador en el VPS si quieres que corra sin sesion interactiva.

set TASK_NAME=MT5AgentMaintenanceHourly
set BOT_DIR=%~dp0

schtasks /Create /TN %TASK_NAME% /SC HOURLY /MO 1 /TR "\"%BOT_DIR%RUN_AGENT_MAINTENANCE_BACKGROUND.bat\"" /F

echo Tarea creada: %TASK_NAME%
pause
