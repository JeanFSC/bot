@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO USDJPY
if not exist logs mkdir logs

:loop
echo. >> logs\bot_jpy.log
echo [%TIME%] ========== PRO USDJPY -- iniciando ========== >> logs\bot_jpy.log
echo [%TIME%] ========== PRO USDJPY -- iniciando ==========
python -m mt5_bot check --config config/pro_jpy.yaml >> logs\bot_jpy.log 2>> logs\check_errors_jpy.log
if errorlevel 1 (
    echo [%TIME%] [USDJPY] CHECK failed -- reintentando en 30s... >> logs\bot_jpy.log
    echo [%TIME%] [USDJPY] CHECK failed -- reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [USDJPY] CHECK OK -- arrancando TRADE loop... >> logs\bot_jpy.log
echo [%TIME%] [USDJPY] CHECK OK -- arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_jpy.yaml --db data/pro_jpy.sqlite --trade-enabled >> logs\bot_jpy.log 2>&1
if errorlevel 1 (
    echo [%TIME%] [USDJPY] Bot crasheo -- reiniciando en 10s... >> logs\bot_jpy.log
    echo [%TIME%] [USDJPY] Bot crasheo -- reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [USDJPY] Bot detenido por el usuario. >> logs\bot_jpy.log
echo [%TIME%] [USDJPY] Bot detenido por el usuario.
pause

