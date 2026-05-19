@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO GBPUSD
if not exist logs mkdir logs

:loop
echo. >> logs\bot_gbpusd.log
echo [%TIME%] ========== PRO GBPUSD -- iniciando ========== >> logs\bot_gbpusd.log
echo [%TIME%] ========== PRO GBPUSD -- iniciando ==========
python -m mt5_bot check --config config/pro_gbp.yaml >> logs\bot_gbpusd.log 2>> logs\check_errors_gbpusd.log
if errorlevel 1 (
    echo [%TIME%] [GBPUSD] CHECK failed -- reintentando en 30s... >> logs\bot_gbpusd.log
    echo [%TIME%] [GBPUSD] CHECK failed -- reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [GBPUSD] CHECK OK -- arrancando TRADE loop... >> logs\bot_gbpusd.log
echo [%TIME%] [GBPUSD] CHECK OK -- arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_gbp.yaml --db data/pro_gbp.sqlite --trade-enabled >> logs\bot_gbpusd.log 2>&1
if errorlevel 1 (
    echo [%TIME%] [GBPUSD] Bot crasheo -- reiniciando en 10s... >> logs\bot_gbpusd.log
    echo [%TIME%] [GBPUSD] Bot crasheo -- reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [GBPUSD] Bot detenido por el usuario. >> logs\bot_gbpusd.log
echo [%TIME%] [GBPUSD] Bot detenido por el usuario.
pause

