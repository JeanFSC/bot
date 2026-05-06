@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTLOG=logs\bot_gold_m5.log
title PRO XAUUSD M5 (Gold 24h)
if not exist logs mkdir logs

:loop
echo. >> %BOTLOG%
echo [%TIME%] ===== PRO GOLD M5 (XAUUSD) iniciando ===== >> %BOTLOG%
python -m mt5_bot check --config config/pro_gold_m5.yaml >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [GOLD M5] CHECK failed — reintentando en 30s >> %BOTLOG%
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [GOLD M5] CHECK OK — arrancando trade loop >> %BOTLOG%
python -m mt5_bot trade --config config/pro_gold_m5.yaml --db data/pro_gold_m5.sqlite --trade-enabled >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [GOLD M5] Bot crasheo — reiniciando en 10s >> %BOTLOG%
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [GOLD M5] Bot detenido por el usuario >> %BOTLOG%
pause
