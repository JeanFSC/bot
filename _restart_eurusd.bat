@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO EURUSD
if not exist logs mkdir logs

:loop
echo. >> logs\bot_eurusd.log
echo [%TIME%] ========== PRO EURUSD -- iniciando ========== >> logs\bot_eurusd.log
echo [%TIME%] ========== PRO EURUSD -- iniciando ==========
python -m mt5_bot check --config config/pro.yaml >> logs\bot_eurusd.log 2>> logs\check_errors_eurusd.log
if errorlevel 1 (
    echo [%TIME%] [EURUSD] CHECK failed -- reintentando en 30s... >> logs\bot_eurusd.log
    echo [%TIME%] [EURUSD] CHECK failed -- reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [EURUSD] CHECK OK -- arrancando TRADE loop... >> logs\bot_eurusd.log
echo [%TIME%] [EURUSD] CHECK OK -- arrancando TRADE loop...
python -m mt5_bot trade --config config/pro.yaml --db data/pro.sqlite --trade-enabled >> logs\bot_eurusd.log 2>&1
if errorlevel 1 (
    echo [%TIME%] [EURUSD] Bot crasheo -- reiniciando en 10s... >> logs\bot_eurusd.log
    echo [%TIME%] [EURUSD] Bot crasheo -- reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [EURUSD] Bot detenido por el usuario. >> logs\bot_eurusd.log
echo [%TIME%] [EURUSD] Bot detenido por el usuario.
pause
