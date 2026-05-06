@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO XAUUSD M5 (Gold 24h)

:loop
echo.
echo [%TIME%] ========== PRO GOLD M5 (XAUUSD) — iniciando ==========
python -m mt5_bot check --config config/pro_gold_m5.yaml 2>> logs\check_errors_gold_m5.log
if errorlevel 1 (
    echo [%TIME%] [GOLD M5] CHECK failed — reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [GOLD M5] CHECK OK — arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_gold_m5.yaml --db data/pro_gold_m5.sqlite --trade-enabled 2>> logs\trade_errors_gold_m5.log
if errorlevel 1 (
    echo [%TIME%] [GOLD M5] Bot crasheo — reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [GOLD M5] Bot detenido por el usuario.
pause
