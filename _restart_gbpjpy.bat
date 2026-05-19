@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO GBPJPY
if not exist logs mkdir logs

:loop
echo. >> logs\bot_gbpjpy.log
echo [%TIME%] ========== PRO GBPJPY -- iniciando ========== >> logs\bot_gbpjpy.log
echo [%TIME%] ========== PRO GBPJPY -- iniciando ==========
python -m mt5_bot check --config config/pro_gbpjpy.yaml >> logs\bot_gbpjpy.log 2>> logs\check_errors_gbpjpy.log
if errorlevel 1 (
    echo [%TIME%] [GBPJPY] CHECK failed -- reintentando en 30s... >> logs\bot_gbpjpy.log
    echo [%TIME%] [GBPJPY] CHECK failed -- reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [GBPJPY] CHECK OK -- arrancando TRADE loop... >> logs\bot_gbpjpy.log
echo [%TIME%] [GBPJPY] CHECK OK -- arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_gbpjpy.yaml --db data/pro_gbpjpy.sqlite %* >> logs\bot_gbpjpy.log 2>&1
if errorlevel 1 (
    echo [%TIME%] [GBPJPY] Bot crasheo -- reiniciando en 10s... >> logs\bot_gbpjpy.log
    echo [%TIME%] [GBPJPY] Bot crasheo -- reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [GBPJPY] Bot detenido por el usuario. >> logs\bot_gbpjpy.log
echo [%TIME%] [GBPJPY] Bot detenido por el usuario.
pause

