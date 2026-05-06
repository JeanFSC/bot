@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTLOG=logs\bot_gbpjpy.log
title PRO GBPJPY
if not exist logs mkdir logs

:loop
echo. >> %BOTLOG%
echo [%TIME%] ===== PRO GBPJPY iniciando ===== >> %BOTLOG%
python -m mt5_bot check --config config/pro_gbpjpy.yaml >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [GBPJPY] CHECK failed — reintentando en 30s >> %BOTLOG%
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [GBPJPY] CHECK OK — arrancando trade loop >> %BOTLOG%
python -m mt5_bot trade --config config/pro_gbpjpy.yaml --db data/pro_gbpjpy.sqlite --trade-enabled >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [GBPJPY] Bot crasheo — reiniciando en 10s >> %BOTLOG%
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [GBPJPY] Bot detenido por el usuario >> %BOTLOG%
pause
