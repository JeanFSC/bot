@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0src
set PYTHONUNBUFFERED=1

echo.
echo ============================================================
echo   MT5 SCALPER DEMO  ^|  EURUSD M1  ^|  EMA 3/8
echo   Profit target: $150 por trade
echo   Lot fijo: 1.0  ^|  SL: 20 pips  ^|  TP: 60 pips
echo   Sin stop-after-action: corre hasta Ctrl+C o equity stop
echo ============================================================
echo.

python -m mt5_bot check --config config/scalper.yaml
if errorlevel 1 (
    echo [ERROR] CHECK fallo. Revisa conexion MT5.
    pause
    exit /b 1
)

echo.
echo [CHECK OK] Iniciando loop de scalping en DEMO REAL...
echo Presiona Ctrl+C para detener.
echo.

python -m mt5_bot trade ^
    --config config/scalper.yaml ^
    --db data/scalper.sqlite ^
    --trade-enabled

echo.
echo ============================================================
echo   LOOP TERMINADO — generando reporte final
echo ============================================================
echo.

python -m mt5_bot report --db data/scalper.sqlite

echo.
pause
