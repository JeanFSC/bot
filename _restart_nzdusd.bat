@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTLOG=logs\bot_nzdusd.log
title PRO NZDUSD
if not exist logs mkdir logs

:loop
echo. >> %BOTLOG%
echo [%TIME%] ===== PRO NZDUSD iniciando ===== >> %BOTLOG%
python -m mt5_bot check --config config/pro_nzdusd.yaml >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [NZDUSD] CHECK failed — reintentando en 30s >> %BOTLOG%
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [NZDUSD] CHECK OK — arrancando trade loop >> %BOTLOG%
python -m mt5_bot trade --config config/pro_nzdusd.yaml --db data/pro_nzdusd.sqlite --trade-enabled >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [NZDUSD] Bot crasheo — reiniciando en 10s >> %BOTLOG%
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [NZDUSD] Bot detenido por el usuario >> %BOTLOG%
pause
