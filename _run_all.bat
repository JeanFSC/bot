@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1
set LOG=%~dp0_run_all.log
echo. > "%LOG%"

echo [%date% %time%] === PASO 2: DRY-RUN (M5 EMA5/13, max 20min) === >> "%LOG%"
python -m mt5_bot trade ^
  --config config/demo_test.yaml ^
  --db data/demo_test.sqlite ^
  --stop-after-action ^
  --max-seconds 1200 >> "%LOG%" 2>&1
set DRY_EXIT=%errorlevel%
echo [%date% %time%] DRY-RUN terminado (exit=%DRY_EXIT%) >> "%LOG%"

echo [%date% %time%] === PASO 3: ORDEN DEMO REAL === >> "%LOG%"
python -m mt5_bot trade ^
  --config config/demo_test.yaml ^
  --db data/demo_test.sqlite ^
  --trade-enabled ^
  --stop-after-action ^
  --max-seconds 1200 >> "%LOG%" 2>&1
echo [%date% %time%] ORDEN terminada (exit=%errorlevel%) >> "%LOG%"

echo [%date% %time%] === PASO 4: REPORTE === >> "%LOG%"
python -m mt5_bot report --db data/demo_test.sqlite >> "%LOG%" 2>&1

echo [%date% %time%] === COMPLETADO === >> "%LOG%"
type "%LOG%"
pause
