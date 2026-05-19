@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
title SANDBOX USDJPY LONDON V2
if not exist logs mkdir logs

echo. >> logs\sandbox_usdjpy_london_v2.log
echo [%TIME%] ========== USDJPY London V2 SANDBOX -- iniciando ========== >> logs\sandbox_usdjpy_london_v2.log
echo [%TIME%] ========== USDJPY London V2 SANDBOX -- iniciando ==========

python -m mt5_bot check --config config/research_usdjpy_london_v2.yaml >> logs\sandbox_usdjpy_london_v2.log 2>> logs\check_errors_usdjpy_london_v2.log
if errorlevel 1 (
    echo [%TIME%] [USDJPY-LONDON-V2] CHECK failed. >> logs\sandbox_usdjpy_london_v2.log
    echo [%TIME%] [USDJPY-LONDON-V2] CHECK failed.
    pause
    exit /b 1
)

echo [%TIME%] [USDJPY-LONDON-V2] CHECK OK -- arrancando DRY-RUN loop... >> logs\sandbox_usdjpy_london_v2.log
echo [%TIME%] [USDJPY-LONDON-V2] CHECK OK -- arrancando DRY-RUN loop...
python -m mt5_bot trade --config config/research_usdjpy_london_v2.yaml --db data/research_usdjpy_london_v2.sqlite >> logs\sandbox_usdjpy_london_v2.log 2>&1

echo [%TIME%] [USDJPY-LONDON-V2] Sandbox detenido. >> logs\sandbox_usdjpy_london_v2.log
echo [%TIME%] [USDJPY-LONDON-V2] Sandbox detenido.
pause
