@echo off
setlocal

cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

if not exist logs mkdir logs
if not exist reports mkdir reports

set COMMAND=%~1
if "%COMMAND%"=="" goto usage
shift /1

if /I "%COMMAND%"=="preflight" goto preflight
if /I "%COMMAND%"=="watchdog" goto watchdog
if /I "%COMMAND%"=="watchdog-bg" goto watchdog_bg
if /I "%COMMAND%"=="maintenance" goto maintenance
if /I "%COMMAND%"=="maintenance-bg" goto maintenance_bg
if /I "%COMMAND%"=="replay-30d" goto replay_30d
if /I "%COMMAND%"=="process-guard" goto process_guard
if /I "%COMMAND%"=="paper-once" goto paper_once
if /I "%COMMAND%"=="demo-once" goto demo_once

echo Unknown command: %COMMAND%
echo.
goto usage

:preflight
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml preflight
exit /b %ERRORLEVEL%

:watchdog
uv run python -m mt5_bot.agent_watchdog --agent-config config/autonomous_agent.yaml --interval-seconds 900 --stale-after-seconds 1200 --report-path data\watchdog_health.jsonl
exit /b %ERRORLEVEL%

:watchdog_bg
uv run python -u -m mt5_bot.agent_watchdog --agent-config config/autonomous_agent.yaml --interval-seconds 900 --stale-after-seconds 3600 --report-path data\watchdog_health.jsonl >> logs\agent_watchdog_service.out.log 2>> logs\agent_watchdog_service.err.log
exit /b %ERRORLEVEL%

:maintenance
uv run python -m mt5_bot.maintenance --agent-config config/autonomous_agent.yaml --reports-dir reports --backups-dir backups --backup-keep 48 --notify
exit /b %ERRORLEVEL%

:maintenance_bg
uv run python -m mt5_bot.maintenance --agent-config config/autonomous_agent.yaml --reports-dir reports --backups-dir backups --backup-keep 48 --notify >> logs\agent_maintenance.out.log 2>> logs\agent_maintenance.err.log
exit /b %ERRORLEVEL%

:replay_30d
uv run python -m mt5_bot.replay --agent-config config/autonomous_agent.yaml --days 30 --out-dir reports --name replay_30d
exit /b %ERRORLEVEL%

:process_guard
uv run python -m mt5_bot.process_guard
exit /b %ERRORLEVEL%

:paper_once
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml run-once
exit /b %ERRORLEVEL%

:demo_once
uv run python -m mt5_bot.agent_runner --agent-config config/autonomous_agent.yaml run-once --allow-demo-orders
exit /b %ERRORLEVEL%

:usage
echo MT5_AGENT.bat ^<command^>
echo.
echo Official commands:
echo   preflight       Validate active autonomous agent configs.
echo   watchdog        Run foreground watchdog. Ctrl+C stops watchdog and child.
echo   watchdog-bg     Run service-style watchdog with logs redirected.
echo   maintenance     Run local report, backup, experiments snapshot, notify.
echo   maintenance-bg  Same as maintenance, with logs redirected.
echo   replay-30d      Generate 30-day replay report.
echo   process-guard   Audit duplicate mt5_bot trade processes.
echo   paper-once      Run active agent once without demo order permission.
echo   demo-once       Run active agent once with demo order permission.
echo.
echo Legacy START_*.bat and _restart_*.bat files may remain for older suites.
echo Prefer this launcher for the autonomous demo agent unless a doc says otherwise.
exit /b 2
