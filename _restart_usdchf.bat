@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO USDCHF

:loop
echo.
echo [%TIME%] ========== PRO USDCHF — iniciando ==========
python -m mt5_bot check --config config/pro_usdchf.yaml 2>> logs\check_errors_usdchf.log
if errorlevel 1 (
    echo [%TIME%] [USDCHF] CHECK failed — reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [USDCHF] CHECK OK — arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_usdchf.yaml --db data/pro_usdchf.sqlite --trade-enabled 2>> logs\trade_errors_usdchf.log
if errorlevel 1 (
    echo [%TIME%] [USDCHF] Bot crasheo — reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [USDCHF] Bot detenido por el usuario.
pause
