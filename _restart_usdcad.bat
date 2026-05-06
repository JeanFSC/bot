@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO USDCAD

:loop
echo.
echo [%TIME%] ========== PRO USDCAD — iniciando ==========
python -m mt5_bot check --config config/pro_usdcad.yaml 2>> logs\check_errors_usdcad.log
if errorlevel 1 (
    echo [%TIME%] [USDCAD] CHECK failed — reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [USDCAD] CHECK OK — arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_usdcad.yaml --db data/pro_usdcad.sqlite --trade-enabled 2>> logs\trade_errors_usdcad.log
if errorlevel 1 (
    echo [%TIME%] [USDCAD] Bot crasheo — reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [USDCAD] Bot detenido por el usuario.
pause
