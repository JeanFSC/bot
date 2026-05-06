@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTLOG=logs\bot_jpy_asia.log
title PRO USDJPY ASIA (nocturno)
if not exist logs mkdir logs

:loop
echo. >> %BOTLOG%
echo [%TIME%] ===== PRO USDJPY ASIA iniciando ===== >> %BOTLOG%
python -m mt5_bot check --config config/pro_jpy_asia.yaml >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [JPY ASIA] CHECK failed — reintentando en 30s >> %BOTLOG%
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [JPY ASIA] CHECK OK — arrancando trade loop >> %BOTLOG%
python -m mt5_bot trade --config config/pro_jpy_asia.yaml --db data/pro_jpy_asia.sqlite --trade-enabled >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [JPY ASIA] Bot crasheo — reiniciando en 10s >> %BOTLOG%
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [JPY ASIA] Bot detenido por el usuario >> %BOTLOG%
pause
