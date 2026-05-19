@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO XAGUSD (Silver)
if not exist logs mkdir logs

:loop
echo. >> logs\bot_silver.log
echo [%TIME%] ========== PRO XAGUSD (Silver) -- iniciando ========== >> logs\bot_silver.log
echo [%TIME%] ========== PRO XAGUSD (Silver) -- iniciando ==========
python -m mt5_bot check --config config/pro_silver.yaml >> logs\bot_silver.log 2>> logs\check_errors_silver.log
if errorlevel 1 (
    echo [%TIME%] [SILVER] CHECK failed -- reintentando en 30s... >> logs\bot_silver.log
    echo [%TIME%] [SILVER] CHECK failed -- reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [SILVER] CHECK OK -- arrancando TRADE loop... >> logs\bot_silver.log
echo [%TIME%] [SILVER] CHECK OK -- arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_silver.yaml --db data/pro_silver.sqlite %* >> logs\bot_silver.log 2>&1
if errorlevel 1 (
    echo [%TIME%] [SILVER] Bot crasheo -- reiniciando en 10s... >> logs\bot_silver.log
    echo [%TIME%] [SILVER] Bot crasheo -- reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [SILVER] Bot detenido por el usuario. >> logs\bot_silver.log
echo [%TIME%] [SILVER] Bot detenido por el usuario.
pause

