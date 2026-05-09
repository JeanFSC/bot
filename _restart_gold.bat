@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO XAUUSD (Gold)
if not exist logs mkdir logs

:loop
echo. >> logs\bot_gold.log
echo [%TIME%] ========== PRO XAUUSD (Gold) -- iniciando ========== >> logs\bot_gold.log
echo [%TIME%] ========== PRO XAUUSD (Gold) -- iniciando ==========
python -m mt5_bot check --config config/pro_gold.yaml >> logs\bot_gold.log 2>> logs\check_errors_gold.log
if errorlevel 1 (
    echo [%TIME%] [GOLD] CHECK failed -- reintentando en 30s... >> logs\bot_gold.log
    echo [%TIME%] [GOLD] CHECK failed -- reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [GOLD] CHECK OK -- arrancando TRADE loop... >> logs\bot_gold.log
echo [%TIME%] [GOLD] CHECK OK -- arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_gold.yaml --db data/pro_gold.sqlite --trade-enabled >> logs\bot_gold.log 2>&1
if errorlevel 1 (
    echo [%TIME%] [GOLD] Bot crasheo -- reiniciando en 10s... >> logs\bot_gold.log
    echo [%TIME%] [GOLD] Bot crasheo -- reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [GOLD] Bot detenido por el usuario. >> logs\bot_gold.log
echo [%TIME%] [GOLD] Bot detenido por el usuario.
pause
