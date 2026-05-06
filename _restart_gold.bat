@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO XAUUSD (Gold)

:loop
echo.
echo [%TIME%] ========== PRO GOLD (XAUUSD) — iniciando ==========
python -m mt5_bot check --config config/pro_gold.yaml 2>> logs\check_errors_gold.log
if errorlevel 1 (
    echo [%TIME%] [GOLD] CHECK failed — reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [GOLD] CHECK OK — arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_gold.yaml --db data/pro_gold.sqlite --trade-enabled 2>> logs\trade_errors_gold.log
if errorlevel 1 (
    echo [%TIME%] [GOLD] Bot crasheo — reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [GOLD] Bot detenido por el usuario.
pause