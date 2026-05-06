@echo off
REM ============================================================
REM  MT5 Bot — Launcher para cuenta DEMO MetaQuotes
REM  Uso: run_demo.bat [dry|trade|report|check|backtest]
REM
REM  MODOS:
REM    dry      Dry-run con config de test (M5 EMA5/13) — NO envia ordenes
REM    trade    Ejecuta 1 orden real DEMO y para
REM    prod     Dry-run con config de produccion (M1 EMA9/21)
REM    report   Muestra metricas de la DB
REM    check    Verifica conexion a MT5 sin operar
REM    backtest Backtest historico (requiere --from y --to)
REM  Sin argumento: dry por defecto
REM ============================================================

cd /d "%~dp0"

if "%1"=="" goto dry
if "%1"=="dry"      goto dry
if "%1"=="trade"    goto trade
if "%1"=="prod"     goto prod
if "%1"=="report"   goto report
if "%1"=="check"    goto check
if "%1"=="backtest" goto backtest
echo Modo desconocido: %1
echo Usa: dry, trade, prod, report, check, backtest
exit /b 1

:dry
echo.
echo === DRY-RUN (config de test: M5 / EMA5/13 / lote 0.01) ===
echo === Ctrl+C para detener ===
echo.
python -m mt5_bot trade ^
  --config config/demo_test.yaml ^
  --db data/demo_test.sqlite ^
  --stop-after-action ^
  --max-seconds 3600
goto end

:trade
echo.
echo === DEMO TRADE REAL — Se enviara 1 orden a MetaQuotes-Demo ===
echo === Config de test: M5 / EMA5/13 / lote minimo 0.01 ===
echo === Ctrl+C para detener ===
echo.
python -m mt5_bot trade ^
  --config config/demo_test.yaml ^
  --db data/demo_test.sqlite ^
  --trade-enabled ^
  --stop-after-action ^
  --max-seconds 3600
goto end

:prod
echo.
echo === DRY-RUN PRODUCCION (M1 / EMA9/21 / percent_equity) ===
echo === Ctrl+C para detener ===
echo.
python -m mt5_bot trade ^
  --config config/demo.yaml ^
  --db data/demo_prod.sqlite ^
  --stop-after-action ^
  --max-seconds 3600
goto end

:report
echo.
echo === REPORTE DB TEST ===
python -m mt5_bot report --db data/demo_test.sqlite
echo.
echo === REPORTE DB PROD ===
python -m mt5_bot report --db data/demo_prod.sqlite 2>nul || echo (No hay datos de produccion aun)
goto end

:check
echo.
echo === VERIFICACION DE CONEXION MT5 ===
python -m mt5_bot check --config config/demo.yaml
goto end

:backtest
echo.
echo === BACKTEST (edita este batch para cambiar fechas) ===
python -m mt5_bot backtest ^
  --config config/demo_test.yaml ^
  --from 2025-01-01 ^
  --to 2025-01-31
goto end

:end
echo.
pause
