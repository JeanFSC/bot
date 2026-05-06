@echo off
REM ============================================================
REM  Auto-test: check -> dry-run -> DEMO real -> report
REM ============================================================
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set LOG=%~dp0_auto_demo.log
echo. > "%LOG%"

echo [%date% %time%] === Verificando Python y dependencias === >> "%LOG%"
python --version >> "%LOG%" 2>&1
python -c "import MetaTrader5; print('MT5 OK')" >> "%LOG%" 2>&1
python -c "import mt5_bot; print('mt5_bot OK')" >> "%LOG%" 2>&1

echo [%date% %time%] === PASO 1: CHECK (conexion MT5) === >> "%LOG%"
python -m mt5_bot check --config config/demo.yaml >> "%LOG%" 2>&1
if errorlevel 1 (
    echo [%date% %time%] CHECK FALLO >> "%LOG%"
    type "%LOG%"
    pause
    exit /b 1
)
echo [%date% %time%] CHECK OK >> "%LOG%"

echo [%date% %time%] === PASO 2: DRY-RUN (M5 EMA5/13, max 20min) === >> "%LOG%"
python -m mt5_bot trade ^
  --config config/demo_test.yaml ^
  --db data/demo_test.sqlite ^
  --stop-after-action ^
  --max-seconds 1200 >> "%LOG%" 2>&1
echo [%date% %time%] DRY-RUN terminado (exit %errorlevel%) >> "%LOG%"

echo [%date% %time%] === PASO 3: ORDEN DEMO REAL === >> "%LOG%"
python -m mt5_bot trade ^
  --config config/demo_test.yaml ^
  --db data/demo_test.sqlite ^
  --trade-enabled ^
  --stop-after-action ^
  --max-seconds 1200 >> "%LOG%" 2>&1
echo [%date% %time%] ORDEN terminada (exit %errorlevel%) >> "%LOG%"

echo [%date% %time%] === PASO 4: REPORTE DB === >> "%LOG%"
python -m mt5_bot report --db data/demo_test.sqlite >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo [%date% %time%] === COMPLETADO === >> "%LOG%"
type "%LOG%"
pause
