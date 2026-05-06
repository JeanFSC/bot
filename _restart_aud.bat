@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTLOG=logs\bot_aud.log
title PRO AUDUSD
if not exist logs mkdir logs

:loop
echo. >> %BOTLOG%
echo [%TIME%] ===== PRO AUDUSD iniciando ===== >> %BOTLOG%
python -m mt5_bot check --config config/pro_aud.yaml >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [AUDUSD] CHECK failed -- reintentando en 30s >> %BOTLOG%
    timeout /t 30 /nobreak >/dev/null
    goto loop
)
echo [%TIME%] [AUDUSD] CHECK OK -- arrancando trade loop >> %BOTLOG%
python -m mt5_bot trade --config config/pro_aud.yaml --db data/pro_aud.sqlite --trade-enabled >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [AUDUSD] Bot crasheo -- reiniciando en 10s >> %BOTLOG%
    timeout /t 10 /nobreak >/dev/null
    goto loop
)
echo [%TIME%] [AUDUSD] Bot detenido por el usuario >> %BOTLOG%
pause
