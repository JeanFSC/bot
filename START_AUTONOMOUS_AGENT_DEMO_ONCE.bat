@echo off
cd /d "%~dp0"
echo WARNING: Esto habilita operaciones en cuenta DEMO si config/autonomous_agent.yaml tiene mode: demo.
echo Verifica preflight antes de continuar.
pause
call MT5_AGENT.bat demo-once
pause
