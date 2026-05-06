@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO NZDUSD

:loop
echo.
echo [%TIME%] ========== PRO NZDUSD — iniciando ==========
python -m mt5_bot check --config config/pro_nzdusd.yaml 2>> logs\check_errors_nzdusd.log
if errorlevel 1 (
    echo [%TIME%] [NZDUSD] CHECK failed — reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [NZDUSD] CHECK OK — arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_nzdusd.yaml --db data/pro_nzdusd.sqlite --trade-enabled 2>> logs\trade_errors_nzdusd.log
if errorlevel 1 (
    echo [%TIME%] [NZDUSD] Bot crasheo — reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [NZDUSD] Bot detenido por el usuario.
pause
