@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title PRO XAUUSD M5 (Gold 24h)
if not exist logs mkdir logs

:loop
echo. >> logs\bot_gold_m5.log
echo [%TIME%] ========== PRO XAUUSD M5 (Gold 24h) -- iniciando ========== >> logs\bot_gold_m5.log
echo [%TIME%] ========== PRO XAUUSD M5 (Gold 24h) -- iniciando ==========
python -m mt5_bot check --config config/pro_gold_m5.yaml >> logs\bot_gold_m5.log 2>> logs\check_errors_gold_m5.log
if errorlevel 1 (
    echo [%TIME%] [GOLD M5] CHECK failed -- reintentando en 30s... >> logs\bot_gold_m5.log
    echo [%TIME%] [GOLD M5] CHECK failed -- reintentando en 30s...
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [GOLD M5] CHECK OK -- arrancando TRADE loop... >> logs\bot_gold_m5.log
echo [%TIME%] [GOLD M5] CHECK OK -- arrancando TRADE loop...
python -m mt5_bot trade --config config/pro_gold_m5.yaml --db data/pro_gold_m5.sqlite --trade-enabled >> logs\bot_gold_m5.log 2>&1
if errorlevel 1 (
    echo [%TIME%] [GOLD M5] Bot crasheo -- reiniciando en 10s... >> logs\bot_gold_m5.log
    echo [%TIME%] [GOLD M5] Bot crasheo -- reiniciando en 10s...
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [GOLD M5] Bot detenido por el usuario. >> logs\bot_gold_m5.log
echo [%TIME%] [GOLD M5] Bot detenido por el usuario.
pause
