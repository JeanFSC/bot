@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTLOG=logs\bot_silver.log
title PRO XAGUSD (Silver 24h)
if not exist logs mkdir logs

:loop
echo. >> %BOTLOG%
echo [%TIME%] ===== PRO SILVER (XAGUSD) iniciando ===== >> %BOTLOG%
python -m mt5_bot check --config config/pro_silver.yaml >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [SILVER] CHECK failed — reintentando en 30s >> %BOTLOG%
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [SILVER] CHECK OK — arrancando trade loop >> %BOTLOG%
python -m mt5_bot trade --config config/pro_silver.yaml --db data/pro_silver.sqlite --trade-enabled >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [SILVER] Bot crasheo — reiniciando en 10s >> %BOTLOG%
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [SILVER] Bot detenido por el usuario >> %BOTLOG%
pause
