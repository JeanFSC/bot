@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO AUDUSD

:loop
echo.
echo [%TIME%] ========== PRO AUDUSD — iniciando ==========
python -m mt5_bot check --config config/pro_aud.yaml 2>> logs\check_errors_aud.log
if errorlevel 1 (
    echo [%TIME%] [AUDUSD] CHECK failed — reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [AUDUSD] CHECK OK — arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_aud.yaml --db data/pro_aud.sqlite --trade-enabled 2>> logs\trade_errors_aud.log
if errorlevel 1 (
    echo [%TIME%] [AUDUSD] Bot crasheo — reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [AUDUSD] Bot detenido por el usuario.
pause