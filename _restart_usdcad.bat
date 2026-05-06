@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set BOTLOG=logs\bot_usdcad.log
title PRO USDCAD
if not exist logs mkdir logs

:loop
echo. >> %BOTLOG%
echo [%TIME%] ===== PRO USDCAD iniciando ===== >> %BOTLOG%
python -m mt5_bot check --config config/pro_usdcad.yaml >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [USDCAD] CHECK failed — reintentando en 30s >> %BOTLOG%
    timeout /t 30 /nobreak >nul
    goto loop
)
echo [%TIME%] [USDCAD] CHECK OK — arrancando trade loop >> %BOTLOG%
python -m mt5_bot trade --config config/pro_usdcad.yaml --db data/pro_usdcad.sqlite --trade-enabled >> %BOTLOG% 2>&1
if errorlevel 1 (
    echo [%TIME%] [USDCAD] Bot crasheo — reiniciando en 10s >> %BOTLOG%
    timeout /t 10 /nobreak >nul
    goto loop
)
echo [%TIME%] [USDCAD] Bot detenido por el usuario >> %BOTLOG%
pause
