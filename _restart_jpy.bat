@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTLOG=logs\bot_jpy.log
title PRO USDJPY
if not exist logs mkdir logs

:loop
echo. >> %BOTLOG%
echo [%TIME%] ===== PRO USDJPY iniciando ===== >> %BOTLOG%
python -m mt5_bot check --config config/pro_jpy.yaml >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [USDJPY] CHECK failed -- reintentando en 30s >> %BOTLOG%
    timeout /t 30 /nobreak >/dev/null
    goto loop
)
echo [%TIME%] [USDJPY] CHECK OK -- arrancando trade loop >> %BOTLOG%
python -m mt5_bot trade --config config/pro_jpy.yaml --db data/pro_jpy.sqlite --trade-enabled >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [USDJPY] Bot crasheo -- reiniciando en 10s >> %BOTLOG%
    timeout /t 10 /nobreak >/dev/null
    goto loop
)
echo [%TIME%] [USDJPY] Bot detenido por el usuario >> %BOTLOG%
pause
