@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTLOG=logs\bot_usdchf.log
title PRO USDCHF
if not exist logs mkdir logs

:loop
echo. >> %BOTLOG%
echo [%TIME%] ===== PRO USDCHF iniciando ===== >> %BOTLOG%
python -m mt5_bot check --config config/pro_usdchf.yaml >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [USDCHF] CHECK failed — reintentando en 30s >> %BOTLOG%
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [USDCHF] CHECK OK — arrancando trade loop >> %BOTLOG%
python -m mt5_bot trade --config config/pro_usdchf.yaml --db data/pro_usdchf.sqlite --trade-enabled >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [USDCHF] Bot crasheo — reiniciando en 10s >> %BOTLOG%
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [USDCHF] Bot detenido por el usuario >> %BOTLOG%
pause
