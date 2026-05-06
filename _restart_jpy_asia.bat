@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO USDJPY ASIA (nocturno)

:loop
echo.
echo [%TIME%] ========== PRO USDJPY ASIA — iniciando ==========
python -m mt5_bot check --config config/pro_jpy_asia.yaml 2>> logs\check_errors_jpy_asia.log
if errorlevel 1 (
    echo [%TIME%] [JPY ASIA] CHECK failed — reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [JPY ASIA] CHECK OK — arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_jpy_asia.yaml --db data/pro_jpy_asia.sqlite --trade-enabled 2>> logs\trade_errors_jpy_asia.log
if errorlevel 1 (
    echo [%TIME%] [JPY ASIA] Bot crasheo — reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [JPY ASIA] Bot detenido por el usuario.
pause
