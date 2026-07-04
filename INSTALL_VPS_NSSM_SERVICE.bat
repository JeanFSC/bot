@echo off
REM Instala el watchdog como servicio Windows usando NSSM.
REM Requisitos en VPS:
REM 1) Instalar MT5 y loguear cuenta demo.
REM 2) Activar Algo Trading.
REM 3) Descargar nssm.exe y ponerlo en C:\nssm\nssm.exe o agregarlo al PATH.
REM 4) Ejecutar este .bat como Administrador.

set SERVICE_NAME=MT5AutonomousAgentWatchdog
set BOT_DIR=%~dp0
set NSSM=C:\nssm\nssm.exe

if not exist "%NSSM%" (
  echo ERROR: No encuentro NSSM en %NSSM%
  echo Descarga NSSM y coloca nssm.exe en C:\nssm\nssm.exe
  pause
  exit /b 1
)

"%NSSM%" install %SERVICE_NAME% "%BOT_DIR%.venv\Scripts\python.exe" -m mt5_bot.agent_watchdog --agent-config config/autonomous_agent.yaml --interval-seconds 900 --stale-after-seconds 3600 --report-path data\watchdog_health.jsonl
"%NSSM%" set %SERVICE_NAME% AppDirectory "%BOT_DIR%"
"%NSSM%" set %SERVICE_NAME% AppStdout "%BOT_DIR%logs\watchdog_stdout.log"
"%NSSM%" set %SERVICE_NAME% AppStderr "%BOT_DIR%logs\watchdog_stderr.log"
"%NSSM%" set %SERVICE_NAME% AppEnvironmentExtra PYTHONIOENCODING=utf-8 PYTHONUTF8=1
"%NSSM%" set %SERVICE_NAME% AppRestartDelay 10000
"%NSSM%" set %SERVICE_NAME% Start SERVICE_AUTO_START

if not exist "%BOT_DIR%logs" mkdir "%BOT_DIR%logs"

echo Servicio instalado: %SERVICE_NAME%
echo Inicia con: net start %SERVICE_NAME%
pause
