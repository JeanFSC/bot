@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTLOG=logs\bot_eurusd.log
title PRO EURUSD
if not exist logs mkdir logs

:loop
echo. >> %BOTLOG%
echo [%TIME%] ===== PRO EURUSD iniciando ===== >> %BOTLOG%
python -m mt5_bot check --config config/pro.yaml >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [EURUSD] CHECK failed -- reintentando en 30s >> %BOTLOG%
    timeout /t 30 /nobreak >/dev/null
    goto loop
)
echo [%TIME%] [EURUSD] CHECK OK -- arrancando trade loop >> %BOTLOG%
python -m mt5_bot trade --config config/pro.yaml --db data/pro.sqlite --trade-enabled >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [EURUSD] Bot crasheo -- reiniciando en 10s >> %BOTLOG%
    timeout /t 10 /nobreak >/dev/null
    goto loop
)
echo [%TIME%] [EURUSD] Bot detenido por el usuario >> %BOTLOG%
pause
