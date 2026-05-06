@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1

echo.
echo ===== DRY-RUN: EMA5/13 M5 (max 20min) =====
echo Ctrl+C para cancelar
echo.
python -m mt5_bot trade --config config/demo_test.yaml --db data/demo_test.sqlite --stop-after-action --max-seconds 1200
echo.
echo DRY-RUN terminado. Exit: %errorlevel%
echo.
echo ===== ORDEN DEMO REAL =====
python -m mt5_bot trade --config config/demo_test.yaml --db data/demo_test.sqlite --trade-enabled --stop-after-action --max-seconds 1200
echo.
echo ORDEN terminada. Exit: %errorlevel%
echo.
echo ===== REPORTE =====
python -m mt5_bot report --db data/demo_test.sqlite
echo.
echo ===== COMPLETADO =====
pause
